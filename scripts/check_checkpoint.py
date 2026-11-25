"""Offline checkpoint checks; run from the repository root with PYTHONPATH=."""
import contextlib, io, json, tempfile
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import URLError, HTTPError
import ingest_weather_fixture as fixture
import ingest_open_meteo as live
import ingest_open_meteo_batch as batch

root=Path.cwd()
with patch('sys.argv',['fixture','fixtures/tangier_forecast.json']), patch.object(fixture,'write_forecast',return_value=SimpleNamespace(returncode=0)) as write:
    assert fixture.main()==0
    payload,source,marker=write.call_args.args
    assert json.loads(payload)['hourly']['precipitation']==[0,None,1.25]
    assert source=='synthetic_tangier' and marker is True
with tempfile.TemporaryDirectory(dir='/tmp') as d:
    p=Path(d)/'invalid.json';p.write_text('{invalid')
    with patch('sys.argv',['fixture',str(p)]),patch.object(fixture,'write_forecast') as write,contextlib.redirect_stderr(io.StringIO()):
        try: fixture.main()
        except SystemExit as e: assert e.code==1
        else: raise AssertionError('malformed fixture accepted')
        write.assert_not_called()
forecast={'utc_offset_seconds':0,'latitude':Decimal('35.7'),'longitude':Decimal('-5.9'),
'hourly_units':{'time':'iso8601',**{k:'test unit' for k in live.HOURLY_FIELDS}},
'hourly':{'time':[(datetime(2026,1,1)+timedelta(hours=h)).strftime('%Y-%m-%dT%H:%M') for h in range(73)],**{k:[0,None]+[Decimal('1.25')]*71 for k in live.HOURLY_FIELDS}}}
live.validate_forecast(forecast)
bad={**forecast,'utc_offset_seconds':3600}
try: live.validate_forecast(bad)
except ValueError: pass
else: raise AssertionError('invalid UTC offset accepted')
assert len(batch.read_points(batch.DEFAULT_POINTS))==11
with patch.object(batch,'fetch_forecast',side_effect=[URLError(TimeoutError('simulated')),('payload',forecast)]) as fetch,patch.object(batch,'sleep'),contextlib.redirect_stderr(io.StringIO()):
    batch.fetch_with_retry('35','-5','test'); assert fetch.call_count==2
with patch.object(batch,'fetch_forecast',side_effect=HTTPError('https://example.invalid',429,'rate limited',{},None)) as fetch,patch.object(batch,'sleep') as sleep:
    try: batch.fetch_with_retry('35','-5','test')
    except HTTPError: pass
    else: raise AssertionError('429 swallowed')
    assert fetch.call_count==1; sleep.assert_not_called()
for responses, success in [([('payload',forecast)]*11,True),([('payload',forecast)]*4+[URLError(TimeoutError('simulated'))],False)]:
    with patch('sys.argv',['batch']),patch.object(batch,'fetch_with_retry',side_effect=responses),patch.object(batch,'sleep'),patch.object(batch,'write_forecast_batch',return_value=SimpleNamespace(returncode=0)) as write,contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        try: batch.main()
        except SystemExit as e: assert not success and e.code==1
        else: assert success
        if success: assert len(write.call_args.args[1])==11
        else: write.assert_not_called()
print('PASS: fixture/null/zero handling, malformed fixture no-write, forecast validation, 11 sampling IDs, bounded retry, no 429 retry, mocked batch success and failure-before-write.')
