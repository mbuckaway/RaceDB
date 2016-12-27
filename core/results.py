from views_common import *
import datetime
from django.utils.translation import ugettext_lazy as _
from views import license_holders_from_search_text

def get_payload_for_result( result ):
	category = result.participant.category
	event = result.event
	competition = event.competition
	wave = event.get_wave_for_category( category )
	if wave.rank_categories_together:
		results = wave.get_results()
		cat_name = wave.name
		cat_type = 'Start Wave'
	else:
		results = event.get_results().filter( participant__category=category ).order_by('status','category_rank')
		cat_name = category.code_gender
		cat_type = 'Component'
	
	payload = {}
	payload['bib'] = result.participant.bib
	payload['raceName'] = u'{} - {}'.format( event.competition.name, event.name )
	payload['raceScheduledStart'] = event.date_time.strftime( '%Y-%m-%d %H:%M' )
	payload['winAndOut'] = event.win_and_out
	payload['isTimeTrial'] = (event.event_type == 1)
	payload['raceIsRunning'] = False
	payload["raceIsUnstarted"] = False
	payload['InfoFields'] = ['LastName', 'FirstName', 'Team', 'License', 'UCIID', 'NatCode', 'City', 'StateProv']
	data = {}
	race_times_all = []
	pos = []
	raceDistance = None
	distance = None
	firstLapDistance = None
	lapDistance = None
	
	units_conversion = 1.0 if competition.distance_unit == 0 else 0.621371
	speed_unit = 'km/h' if competition.distance_unit == 0 else 'mph'
	distance_unit = 'km' if competition.distance_unit == 0 else 'miles'
	
	for rr in results:
		p = rr.participant
		h = p.license_holder
		race_times = rr.get_race_times()
		d = {
			'LastName': h.last_name,
			'FirstName': h.first_name,
			'Team':		p.team.name if p.team else u'',
			'License':	h.license_code_trunc,
			'UCIID':	h.uci_id,
			'NatCode':	h.nation_code,
			'Gender':	('Men','Women')[h.gender],
			'City':		h.city,
			'StateProv':h.state_prov,
			
			'raceTimes': race_times,
			'interp':	[0] * len(race_times),
			'lastTime': race_times[-1] if race_times else 0.0,
			'lastTimeOrig': race_times[-1] if race_times else 0.0,
			'status':	rr.status_text,
		}
		if rr.ave_kmh:
			d['speed'] = u'{:.2f} {}'.format(rr.ave_kmh*units_conversion, speed_unit)
			if raceDistance is None and race_times:
				raceDistance = units_conversion * rr.ave_kmh * (race_times[-1] - race_times[0])/(60.0*60.0)
		
		lap_speeds = rr.get_lap_kmh()
		if lap_speeds:
			if units_conversion != 1.0:
				lap_speeds = [s*units_conversion for s in lap_speeds]
			d['lapSpeeds'] = lap_speeds
			if firstLapDistance is None:
				try:
					firstLapDistance = lap_speeds[0] * (race_times[1] - race_times[0])/(60.0*60.0)
				except:
					pass
				try:
					lapDistance = lap_speeds[1] * (race_times[2] - race_times[1])/(60.0*60.0)
				except:
					pass
				
		data[p.bib] = d
		pos.append( p.bib )
		race_times_all.append( race_times )
		
	gapValue = []
	winner_finish = race_times_all[0][-1]
	winner_laps = len(race_times_all[0])
	for rt in race_times_all:
		if len(race_times_all[0]) != len(rt):
			gapValue.append( len(rt) - winner_laps )
		else:
			gapValue.append( rt[-1] - winner_finish )
	
	catDetails = {
		'name':	cat_name,
		'catType':cat_type,
		'pos': pos,
		'gapValue': gapValue,
		'laps':	winner_laps,
		'startOffset': 0,
	}
	if raceDistance:
		catDetails['raceDistance'] = raceDistance
	if firstLapDistance and firstLapDistance != lapDistance:
		catDetails['firstLapDistance'] = firstLapDistance
	if lapDistance:
		catDetails['lapDistance'] = lapDistance
	payload['catDetails'] = [catDetails]
	payload['data'] = data
	return payload

def ResultsMassStart( request, eventId ):
	time_stamp = datetime.datetime.now()
	event = get_object_or_404( EventMassStart, pk=eventId )
	return render( request, 'results_mass_start_list.html', locals() )

def ResultsMassStartCategory( request, eventId, categoryId ):
	event = get_object_or_404( EventMassStart, pk=eventId )
	category = get_object_or_404( Category, pk=categoryId )
	wave = event.get_wave_for_category( category )
	if wave.rank_categories_together:
		results = wave.get_results()
	else:
		results = event.get_results().filter( participant__category=category ).order_by('status','category_rank')
	num_nationalities = results.exclude(participant__license_holder__nation_code='').values('participant__license_holder__nation_code').distinct().count()
	num_starters = results.exclude( status=Result.cDNS ).count()
	time_stamp = datetime.datetime.now()
	return render( request, 'results_mass_start_category_list.html', locals() )

def ResultMassStartRiderAnaysis( request, resultId ):
	result = get_object_or_404( ResultMassStart, pk=resultId )
	payload = get_payload_for_result( result )
	return render( request, 'RiderDashboard.html', locals() )

#---------------------------------------------------------------------------------------------
	
def ResultsTT( request, eventId ):
	time_stamp = datetime.datetime.now()
	event = get_object_or_404( EventMassStart, pk=eventId )
	return render( request, 'results_tt_list.html', locals() )

