import re
import sys
import datetime
from collections import namedtuple, defaultdict

from django.db import transaction, IntegrityError
from django.db.models import Q

from xlrd import open_workbook, xldate_as_tuple
import import_utils
from CountryIOC import ioc_from_country
from import_utils import *
from models import *
from FieldMap import standard_field_map, normalize 

def license_holder_import_excel( worksheet_name='', worksheet_contents=None, message_stream=sys.stdout, update_license_codes=False ):
	tstart = datetime.datetime.now()

	if message_stream == sys.stdout or message_stream == sys.stderr:
		def message_stream_write( s ):
			message_stream.write( removeDiacritic(s) )
	else:
		def message_stream_write( s ):
			message_stream.write( unicode(s) )
	
	#-------------------------------------------------------------------------------------------------
	discipline_cols = {
		'Road':				['national road', 'provincial road'],
		'Cyclocross':		['national cyclocross', 'provincial cyclocross'],
		'Track':			['track'],
		'MTB':				['cross country', 'provincial cross country', 'downhill', 'fourx'],
		'Para':				['para cycling'],
	}
	discipline_by_name = {}
	for dname in discipline_cols.iterkeys():
		try:
			discipline_by_name[dname] = Discipline.objects.get(name=dname)
		except (Discipline.DoesNotExist,  Discipline.MultipleObjectsReturned):
			pass
	#-------------------------------------------------------------------------------------------------
	
	cpy_prefix = '_CPY_'
	dup_prefix = '_DUP_'
	err_prefix = '_XXX_'
	
	# Clean up all existing cpy or dup codes.
	success = True
	while success:
		success = False
		with transaction.atomic():
			for lh in LicenseHolder.objects.filter( license_code__startswith=cpy_prefix )[:999]:
				lh.license_code = lh.license_code.replace( cpy_prefix, err_prefix )
				lh.save()
				success = True
	success = True
	while success:
		success = False
		with transaction.atomic():
			for lh in LicenseHolder.objects.filter( license_code__startswith=dup_prefix )[:999]:
				lh.license_code = lh.license_code.replace( dup_prefix, err_prefix )
				lh.save()
				success = True

	ifm = standard_field_map()
	
	status_count = defaultdict( int )
	
	license_code_aliases = []
	
	# Process the records in large transactions for efficiency.
	def process_ur_records( ur_records ):
		for i, ur in ur_records:
			v = ifm.finder( ur )
			
			#-----------------------------------------------------------------------------------------
			# Process all the fields from the Excel sheet.
			#
			uci_code		= to_str(v('uci_code', None))
			date_of_birth	= v('date_of_birth', None)
			
			try:
				date_of_birth = date_from_value(date_of_birth)
			except Exception as e:
				message_stream_write( 'Row {}: Ignoring birthdate (must be YYYY-MM-DD) "{}" ({}) {}'.format(
					i, date_of_birth, ur, e)
				)
				date_of_birth = None
			
			# If no date of birth, try to get it from the UCI code.
			if not date_of_birth and uci_code:
				try:
					date_of_birth = datetime.date( int(uci_code[3:7]), int(uci_code[7:9]), int(uci_code[9:11]) )
				except:
					pass
			
			# As a last resort, pick the default DOB
			date_of_birth 	= date_of_birth or invalid_date_of_birth
			
			license_code = None
			for lc in license_code_aliases:
				license_code = to_int_str(v(lc, None))
				if license_code is not None:
					license_code = license_code.upper().strip()
					if license_code:
						break
			if not license_code or license_code == u'TEMP':
				license_code = None
			
			last_name		= to_str(v('last_name',u''))
			first_name		= to_str(v('first_name',u''))
			name			= to_str(v('name',u''))
			if not name:
				name = ' '.join( n for n in [first_name, last_name] if n )
			
			gender			= to_str(v('gender',u''))
			gender			= gender_from_str(gender) if gender else None
			
			email			= to_str(v('email', None))
			phone			= to_str(v('phone', None))
			city			= to_str(v('city', None))
			state_prov		= to_str(v('state_prov', None))
			zip_postal		= to_str(v('zip_postal', None))
			if zip_postal:
				zip_postal = validate_postal_code( zip_postal )
			nationality		= to_str(v('nationality', None))
			
			uci_id			= to_uci_id(v('uci_id', None))
			nation_code		= to_str(v('nation_code', None))
			
			bib				= (to_int(v('bib', None)) or None)
			tag				= to_int_str(v('tag', None))
			note		 	= to_str(v('note', None))
			
			emergency_contact_name = to_str(v('emergency_contact_name', None))
			emergency_contact_phone = to_str(v('emergency_contact_phone', None))

			team_name		= to_str(v('team', None))
			club_name		= to_str(v('club', None))
			if not team_name:
				team_name = club_name
			team_code		= to_str(v('team_code', None))

			#---------------------------------------------
			
			license_holder_attr_value = {
				'license_code':license_code,
				'last_name':last_name,
				'first_name':first_name,
				'gender':gender,
				'date_of_birth':date_of_birth,
				'uci_code':uci_code,
				'emergency_contact_name':emergency_contact_name,
				'emergency_contact_phone':emergency_contact_phone,
				'email':email,
				'city':city,
				'state_prov':state_prov,
				'nationality':nationality,
				'zip_postal':zip_postal,
				
				'nation_code':nation_code,
				'uci_id':uci_id,
				
				'existing_tag':tag,
				'existing_bib':bib,
				'note':note,
			}
			license_holder_attr_value = { a:v for a, v in license_holder_attr_value.iteritems() if v }
			
			#------------------------------------------------------------------------------
			# Update Team
			#
			if team_name:
				do_save = False
				team = Team.objects.filter( search_text__startswith=utils.get_search_text([team_name])).first()
				if not team:
					team = Team( name=team_name )
					do_save = True
				if team_code and team.team_code != team_code:
					team.team_code = team_code
					do_save = True
				if do_save:
					msg = u'Row {:>6}: Updated team: {}\n'.format(
						i,
						u', '.join( unicode(v) if v else u'None' for v in [team_name, team_code,] ),
					)
					message_stream_write( msg )
					print removeDiacritic(msg)[:-1]
					team.save()
			
			#------------------------------------------------------------------------------
			# Get LicenseHolder.
			#
			license_holder = None
			status = 'Unchanged'
			
			# Get a query by Last, First, DOB and Gender.
			qNameDOBGender = Q( search_text__startswith=utils.get_search_text([last_name, first_name]) )
			if date_of_birth and date_of_birth != invalid_date_of_birth:
				qNameDOBGender &= Q( date_of_birth=date_of_birth )
			if gender is not None:
				qNameDOBGender &= Q( gender=gender )
			
			#------------------------------------------------------------------------------
			if update_license_codes:
				# Try to find the license holder by name, DOB, gender
				try:
					license_holder = LicenseHolder.objects.get( qNameDOBGender )
					
					# Check if there is another license holder with this license code.  If so, make it unique.
					if license_holder_attr_value.get('license_code', None):
						lc_license_holder = LicenseHolder.objects.filter( license_code=license_holder_attr_value['license_code'] ).first()
						if lc_license_holder and lc_license_holder.id != license_holder.id:
							lc_license_holder.license_code = random_temp_license()
							lc_license_holder.save()
				
				except LicenseHolder.DoesNotExist:
					# Create a new license holder from the information given.
					try:
						if 'license_code' not in license_holder_attr_value:
							license_holder_attr_value['license_code'] = license_code = random_temp_license()
						else:
							# Check if there is an existing license holder with this license code.  If so, make it unique.
							lc_license_holder = LicenseHolder.objects.filter( license_holder_attr_value['license_code'] ).first()
							if lc_license_holder:
								lc_license_holder.license_code = random_temp_license()
								lc_license_holder.save()
						
						license_holder = LicenseHolder( **license_holder_attr_value )
						license_holder.save()
						status = 'Added'
					
					except Exception as e:
						message_stream_write( u'**** Row {}: New License Holder Exception: {}, Name="{}"\n'.format(
								i, e, name,
							)
						)
						continue
				
				except LicenseHolder.MultipleObjectsReturned:
					message_stream_write( u'**** Row {}: found multiple LicenceHolders matching "Last, First DOB Gender" Name="{}"\n'.format(
							i, name,
						)
					)
					continue
					
			#------------------------------------------------------------------------------
			if not license_holder and uci_id:
				try:
					license_holder = LicenseHolder.objects.get( uci_id=uci_id )
				except LicenseHolder.DoesNotExist:
					pass
				except LicenseHolder.MultipleObjectsReturned:
					message_stream_write( u'**** Row {}: Warning!  Name="{}" found duplicate UCIID="{}"\n'.format(
							i, name, uci_id,
						)
					)
					pass
				
			if not license_holder and license_code:
				# Try to find the license holder by license code.
				try:
					license_holder = LicenseHolder.objects.get( license_code=license_code )
				except LicenseHolder.DoesNotExist:
					# No match.  Create a new license holder using the given license code.
					try:
						license_holder = LicenseHolder( **license_holder_attr_value )
						license_holder.save()
						del license_holder_attr_value['license_code'] # Delete license_code after creating a record to prevent the update.
						status = 'Added'
					except Exception as e:
						message_stream_write( u'**** Row {}: New License Holder Exception: {}, Name="{}"\n'.format(
								i, e, name,
							)
						)
						continue
						
			if not license_holder:
				# Try to find the license holder by name, DOB, gender
				try:
					license_holder = LicenseHolder.objects.get( qNameDOBGender )
				except LicenseHolder.DoesNotExist:
					# No name match.
					# Create a temporary license holder.
					try:
						license_holder_attr_value['license_code'] = random_temp_license()
						license_holder = LicenseHolder( **license_holder_attr_value )
						license_holder.save()
						del license_holder_attr_value['license_code'] # Delete license_code after creating a record to prevent the update.
						status = 'Added'
					
					except Exception as e:
						message_stream_write( u'**** Row {}: New License Holder Exception: {}, Name="{}"\n'.format(
								i, e, name,
							)
						)
						continue
				
				except LicenseHolder.MultipleObjectsReturned:
					message_stream_write( u'**** Row {}: found multiple LicenceHolders matching "Last, First DOB Gender" Name="{}"\n'.format(
							i, name,
						)
					)
					continue
				
			if not license_holder:
				message_stream_write( u'**** Row {}: Cannot find License Holder: {}, Name="{}"\n'.format(
						i, e, name,
					)
				)
				continue
				
			fields_changed = set_attributes_changed( license_holder, license_holder_attr_value, False )
			if fields_changed:
				try:
					license_holder.save()
					if status != 'Added':
						status = 'Changed'
				except Exception as e:
					message_stream_write( u'**** Row {}: License Holder Exception: {}, Name="{}"\n'.format(
							i, e, name,
						)
					)
					message_stream.write( u'^^^^ {}\n'.format( u', '.join( u'{}={}'.format(k, v) for k, v in license_holder_attr_value.iteritems()) ) )
					continue
			
			status_count[status] += 1
			if status != 'Unchanged':
				msg = u'Row {:>6}: {}: {:>8} {}\n'.format(
					i,
					status,
					license_holder.license_code,
					u', '.join( unicode(v) if v else u'None' for v in [
							license_holder.date_of_birth.strftime('%Y-%m-%d'), license_holder.nation_code, license_holder.uci_id,
							u'{} {}'.format(license_holder.first_name, license_holder.last_name),
							license_holder.city, license_holder.state_prov,
							license_holder.emergency_contact_name, license_holder.emergency_contact_phone,
						]
					),
				)
				msg += u'            {}\n'.format( u', '.join( u'{}=({})'.format(k,v) for k,v in fields_changed ) )
				message_stream_write( msg )
				print removeDiacritic(msg)[:-1]

	sheet_name = None
	if worksheet_contents is not None:
		wb = open_workbook( file_contents = worksheet_contents )
	else:
		try:
			fname, sheet_name = worksheet_name.split('$')
		except:
			fname = worksheet_name
		wb = open_workbook( fname )
	
	ur_records = []
	import_utils.datemode = wb.datemode
	
	ws = None
	for cur_sheet_name in wb.sheet_names():
		if cur_sheet_name == sheet_name or sheet_name is None:
			message_stream_write( u'Reading sheet: {}\n'.format(cur_sheet_name) )
			ws = wb.sheet_by_name(cur_sheet_name)
			break
	
	if not ws:
		message_stream_write( u'Cannot find sheet "{}"\n'.format(sheet_name) )
		return
	
	print 'Process all rows in spreadsheet...'
	num_rows = ws.nrows
	num_cols = ws.ncols
	for r in xrange(num_rows):
		row = ws.row( r )
		if r == 0:
			# Get the header fields from the first row.
			fields = [unicode(f.value).strip() for f in row]
			ifm.set_headers( fields )
			license_code_aliases = [lh for lh in ifm.name_to_col.iterkeys() if lh.startswith('license_code')]
			
			message_stream_write( u'Header Row:\n' )
			for col, f in enumerate(fields, 1):
				name = ifm.get_name_from_alias( f )
				if name is not None:
					message_stream_write( u'        {}. {} --> {}\n'.format(col, f, name) )
				else:
					message_stream_write( u'        {}. ****{} (Ignored)\n'.format(col, f) )
			message_stream_write( u'\n' )
			continue
			
		ur_records.append( (r+1, [v.value for v in row]) )
		if len(ur_records) == 1000:
			process_ur_records( ur_records )
			ur_records = []
			
	process_ur_records( ur_records )
	
	message_stream_write( u'\n' )
	message_stream_write( u'   '.join( u'{}: {}'.format(a, v) for a, v in sorted((status_count.iteritems()), key=lambda x:x[0]) ) )
	message_stream_write( u'\n' )
	message_stream_write( u'Initialization in: {}\n'.format(datetime.datetime.now() - tstart) )
