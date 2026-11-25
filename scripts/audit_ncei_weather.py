"""Read-only audit of the single hashed TERRALERT NCEI source; no database access."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timedelta, timezone, date
import hashlib
import json
import math
from pathlib import Path
import re
from zoneinfo import ZoneInfo

SHA = 'd1d534a32ed5c907a491f5712379d6dc80786bbe68c05dd56539e07c52cd10a1'
UTC = timezone.utc
LOCAL = ZoneInfo('Africa/Casablanca')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    digest = hashlib.sha256(args.source.read_bytes()).hexdigest()
    if digest != SHA:
        raise ValueError('Source checksum differs from audited file')
    args.output.mkdir(parents=True, exist_ok=True)
    stats = defaultdict(Counter)
    data = defaultdict(lambda: defaultdict(list))
    meta = Counter(); qcs = Counter(); missing = Counter(); reports = Counter()
    exact = Counter(); raw_seen = set(); mismatch = 0; widths = Counter()
    with args.source.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f); header = next(reader)
        for line, row in enumerate(reader, 2):
            widths[len(row)] += 1
            if len(row) != len(header):
                raise ValueError(f'Row width error on line {line}')
            mismatch += row[7] != row[17]
            r = dict(zip(header, row))  # repeated REPORT_TYPE equality is checked below
            station = r['STATION']
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', r['DATE']):
                raise ValueError(f'Unexpected timestamp on line {line}')
            t = datetime.fromisoformat(r['DATE']).replace(tzinfo=UTC)
            k = (station, t.year); stats[k]['rows'] += 1
            rh = hashlib.sha256(json.dumps(row).encode()).digest()
            if rh in raw_seen: exact[k] += 1
            raw_seen.add(rh)
            meta[(station, r['NAME'], r['LATITUDE'], r['LONGITUDE'], r['ELEVATION'])] += 1
            reports[r['REPORT_TYPE']] += 1
            m = re.fullmatch(r'([+-]\d{4}),([0-9A-Z])', r['TMP'])
            value = None
            if not m:
                missing['malformed_or_blank'] += 1; stats[k]['malformed'] += 1
            else:
                n = int(m[1]); q = m[2]; qcs[q] += 1
                if n == 9999:
                    missing[r['TMP']] += 1; stats[k]['missing'] += 1
                else:
                    stats[k]['numeric'] += 1
                    if q in {'1', '5'} and -932 <= n <= 618:
                        value = n; stats[k]['valid_rows'] += 1
                        stats[k]['zero_rows'] += n == 0
                        stats[k]['negative_rows'] += n < 0
                    else:
                        stats[k]['excluded_numeric'] += 1
            data[station][t].append(value)
    assert mismatch == 0, 'Repeated REPORT_TYPE columns differ'
    annual=[]; daily=[]; gap_rows=[]; summaries=[]; examples=[]; all_conflicts=[]
    for station, grouped in sorted(data.items()):
        clean={}; conflicts=[]
        for t, values in grouped.items():
            k=(station,t.year); stats[k]['unique_times'] += 1
            if len(values)>1:
                stats[k]['duplicate_groups'] += 1
                stats[k]['duplicate_extra_rows'] += len(values)-1
            good={v for v in values if v is not None}
            if len(good)==1: clean[t]=good.pop()
            elif len(good)>1:
                stats[k]['conflicting_times'] += 1
                conflicts.append({'station':station,'utc':t.isoformat(),'values_c':sorted(v/10 for v in good)})
        all_conflicts.extend(conflicts)
        local_obs=defaultdict(list)
        for t,v in sorted(clean.items()): local_obs[t.astimezone(LOCAL).date()].append((t,v))
        for year in range(2000,2026):
            start=datetime(year,1,1,tzinfo=UTC); end=datetime(year+1,1,1,tzinfo=UTC)
            obs=sorted(t for t in grouped if start<=t<end)
            valid=sorted(t for t in clean if start<=t<end)
            occupied={int((t-start).total_seconds()//3600) for t in valid}
            present={int((t-start).total_seconds()//3600) for t in obs}
            nh=int((end-start).total_seconds()/3600)
            longest=0; run=0; run_start=None
            for hour in range(nh+1):
                if hour<nh and hour not in occupied:
                    if run==0: run_start=hour
                    run+=1;longest=max(longest,run)
                elif run:
                    if run>=24:
                        gap_rows.append(dict(station=station,year=year,start_utc=(start+timedelta(hours=run_start)).isoformat(),end_utc_exclusive=(start+timedelta(hours=hour)).isoformat(),missing_hour_bins=run))
                    run=0
            d=date(year,1,1); stop=date(year+1,1,1); passed=0; anydays=0
            while d<stop:
                a=datetime.combine(d,datetime.min.time(),LOCAL).astimezone(UTC)
                b=datetime.combine(d+timedelta(days=1),datetime.min.time(),LOCAL).astimezone(UTC)
                items=local_obs[d]; times=[t for t,v in items]; hours=int((b-a).total_seconds()/3600)
                bins={int((t-a).total_seconds()//3600) for t in times}
                edge=[a]+times+[b]
                maxgap=max((y-x).total_seconds()/3600 for x,y in zip(edge,edge[1:]))
                ok=len(bins)>=math.ceil(.75*hours) and maxgap<=3
                passed+=ok; anydays+=bool(items)
                day=dict(station=station,date=str(d),day_hours=hours,valid_times=len(items),occupied_hours=len(bins),required_hours=math.ceil(.75*hours),max_gap_hours=maxgap,eligible=ok,min_c=min((v/10 for t,v in items),default=None),max_c=max((v/10 for t,v in items),default=None))
                daily.append(day)
                if ok and not examples:
                    examples.append(dict(**day,observations=[{'utc':t.isoformat(),'local':t.astimezone(LOCAL).isoformat(),'temperature_c':v/10} for t,v in items]))
                d+=timedelta(days=1)
            row=dict(station=station,year=year,**{key:stats[(station,year)][key] for key in ('rows','numeric','valid_rows','zero_rows','negative_rows','missing','excluded_numeric','unique_times','duplicate_groups','duplicate_extra_rows','conflicting_times')},usable_unique_times=len(valid),exact_duplicate_rows=exact[(station,year)],missing_report_hours=nh-len(present),missing_valid_hours=nh-len(occupied),longest_missing_valid_hours=longest,local_days_with_valid=anydays,eligible_local_days=passed,calendar_days=(stop-date(year,1,1)).days)
            annual.append(row)
        times=sorted(grouped); validtimes=sorted(clean)
        deltas=Counter((b-a).total_seconds()/60 for a,b in zip(times,times[1:]))
        summaries.append(dict(station=station,first_utc=times[0].isoformat(),last_utc=times[-1].isoformat(),first_valid_utc=validtimes[0].isoformat(),last_valid_utc=validtimes[-1].isoformat(),rows=sum(map(len,grouped.values())),unique_times=len(grouped),usable_times=len(clean),conflict_count=len(conflicts),conflict_examples=conflicts[:10],top_time_steps_minutes=deltas.most_common(10),min_c=min(clean.values())/10,max_c=max(clean.values())/10))
    for name, rows in [('annual',annual),('daily',daily),('gaps_24h',gap_rows)]:
        with (args.output/(name+'.csv')).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (args.output/'conflicting_timestamps.json').write_text(json.dumps(all_conflicts,indent=2))
    result=dict(sha256=digest,bytes=args.source.stat().st_size,header=header,row_widths=dict(widths),repeated_report_type_differences=mismatch,metadata=[dict(station=k[0],name=k[1],latitude=k[2],longitude=k[3],elevation=k[4],rows=v) for k,v in meta.items()],quality_counts=dict(qcs),missing_encodings=dict(missing),report_types=dict(reports),stations=summaries,annual=annual,eligible_days=sum(r['eligible'] for r in daily),worked_example=examples[0])
    (args.output/'summary.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in {'annual','worked_example'}},indent=2))
    print('Eligible local days:',result['eligible_days'])

if __name__=='__main__': main()
