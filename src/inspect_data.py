from pathlib import Path
import zipfile, json, hashlib, urllib.request
from collections import Counter, defaultdict
import pandas as pd

MONTHS = ['202606','202607','202608']
BASE_URL = 'https://s3.amazonaws.com/capitalbikeshare-data/'

def inspect_data(root):
    root=Path(root); reports=root/'reports'; reports.mkdir(exist_ok=True)
    summaries=[]; missing=[]; schemas={}; samples=[]; daily=[]
    all_ids=Counter(); station_pairs=Counter()
    for month in MONTHS:
        archive=root/'data/raw'/f'{month}-capitalbikeshare-tripdata.zip'
        with zipfile.ZipFile(archive) as z:
            members=[n for n in z.namelist() if n.endswith('.csv') and not n.startswith('__MACOSX/')]
            frames=[pd.read_csv(z.open(n),dtype='string',keep_default_na=False) for n in members]
        df=pd.concat(frames,ignore_index=True)
        schemas[month]={'columns':list(df.columns),'read_policy':'All raw fields loaded as strings; blank or whitespace-only fields counted as missing.'}
        n=len(df); blank=df.apply(lambda s:s.str.strip().eq(''))
        for col in df:
            count=int(blank[col].sum()); missing.append({'month':month,'column':col,'missing_count':count,'missing_percent':100*count/n})
        start=pd.to_datetime(df.started_at,format='mixed',errors='coerce'); end=pd.to_datetime(df.ended_at,format='mixed',errors='coerce')
        duration=(end-start).dt.total_seconds()
        ids=df.ride_id.str.strip(); valid_ids=ids[~blank.ride_id]; counts=Counter(valid_ids.tolist()); all_ids.update(counts)
        summary={'month':month,'trip_records':n,'missing_start_station_ids':int(blank.start_station_id.sum()),'missing_end_station_ids':int(blank.end_station_id.sum()),'missing_start_station_ids_percent':100*blank.start_station_id.mean(),'missing_end_station_ids_percent':100*blank.end_station_id.mean(),'duplicate_ride_id_excess_rows':sum(v-1 for v in counts.values()),'distinct_duplicated_ride_ids':sum(v>1 for v in counts.values()),'missing_ride_ids':int(blank.ride_id.sum()),'exact_duplicate_excess_rows':int(df.duplicated().sum()),'invalid_or_missing_start_timestamps':int(start.isna().sum()),'invalid_or_missing_end_timestamps':int(end.isna().sum()),'end_before_start':int((duration<0).sum()),'zero_duration':int((duration==0).sum()),'duration_under_60_seconds':int(((duration>=0)&(duration<60)).sum()),'duration_over_24_hours':int((duration>86400).sum()),'earliest_start':str(start.min()),'latest_start':str(start.max()),'earliest_end':str(end.min()),'latest_end':str(end.max()),'starts_outside_source_month':int((start.notna() & start.dt.strftime('%Y%m').ne(month)).sum()),'both_station_ids_missing':int((blank.start_station_id & blank.end_station_id).sum()),'both_station_ids_present':int((~blank.start_station_id & ~blank.end_station_id).sum())}
        for side in ['start','end']:
            lat=pd.to_numeric(df[f'{side}_lat'],errors='coerce'); lon=pd.to_numeric(df[f'{side}_lng'],errors='coerce')
            summary[f'{side}_missing_coordinate_rows']=int((blank[f'{side}_lat']|blank[f'{side}_lng']).sum())
            summary[f'{side}_invalid_nonblank_coordinate_rows']=int(((~blank[f'{side}_lat'] & (lat.isna()|~lat.between(-90,90))) | (~blank[f'{side}_lng'] & (lon.isna()|~lon.between(-180,180)))).sum())
            summary[f'{side}_zero_coordinate_rows']=int(((lat==0)|(lon==0)).sum())
            usable=~blank[f'{side}_station_id'] & ~blank[f'{side}_station_name']
            pairs=df.loc[usable,[f'{side}_station_id',f'{side}_station_name']].apply(lambda s:s.str.strip())
            station_pairs.update(map(tuple,pairs.itertuples(index=False,name=None)))
        summaries.append(summary)
        sample=df.head(10).copy(); sample['source_month']=month; samples.append(sample)
        date_counts=start.dt.strftime('%Y-%m-%d').value_counts().sort_index()
        daily.extend({'source_month':month,'date':date,'trip_starts':int(count)} for date,count in date_counts.items())
        print(f'{month}: {n:,} trips inspected',flush=True)
    result=pd.DataFrame(summaries); result.to_csv(reports/'monthly_quality_summary.csv',index=False)
    pd.DataFrame(missing).to_csv(reports/'missing_values_by_column.csv',index=False)
    pd.concat(samples).to_csv(reports/'sample_trips.csv',index=False)
    pd.DataFrame(daily).to_csv(reports/'daily_trip_counts.csv',index=False)
    (reports/'schemas.json').write_text(json.dumps(schemas,indent=2))
    names=defaultdict(set); ids_by_name=defaultdict(set)
    for (sid,name),count in station_pairs.items(): names[sid].add(name); ids_by_name[name].add(sid)
    pd.DataFrame([{'station_id':sid,'station_name':name,'endpoint_occurrences':count,'names_for_this_id':len(names[sid]),'ids_for_this_name':len(ids_by_name[name])} for (sid,name),count in sorted(station_pairs.items())]).to_csv(reports/'station_id_name_inventory.csv',index=False)
    overview={'total_records':int(result.trip_records.sum()),'same_column_names_and_order':all(schemas[m]['columns']==schemas[MONTHS[0]]['columns'] for m in MONTHS),'global_duplicate_ride_id_excess_rows':sum(v-1 for v in all_ids.values()),'cross_month_duplicate_excess_rows':sum(v-1 for v in all_ids.values())-int(result.duplicate_ride_id_excess_rows.sum()),'station_ids_with_multiple_names':sum(len(v)>1 for v in names.values()),'station_names_with_multiple_ids':sum(len(v)>1 for v in ids_by_name.values()),'unique_nonblank_station_ids_with_names':len(names),'no_records_modified_or_removed':True}
    (reports/'overview.json').write_text(json.dumps(overview,indent=2))
    calendar=pd.DataFrame({'date':pd.date_range('2026-06-01','2026-08-31')})
    calendar['month']=calendar.date.dt.strftime('%Y%m'); calendar['day_type']=calendar.date.dt.dayofweek.map(lambda d:'weekend' if d>=5 else 'weekday')
    calendar['holiday_note']=calendar.date.dt.strftime('%Y-%m-%d').map({'2026-06-19':'Juneteenth','2026-07-03':'Independence Day observed','2026-07-04':'Independence Day'}).fillna('')
    calendar.to_csv(reports/'study_calendar.csv',index=False)
    return result,overview

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    result,overview=inspect_data(root)
    print(result.to_string(index=False)); print(json.dumps(overview,indent=2))
