#!/usr/bin/env bash
# phone-net-ICKS Wi-Fi pull (2026-11-13): pull a phone over adb wireless debugging, no cable.
# Read-only on the phone. Texts + MMS index + call log since SINCE, new media since SINCE (internal + SD), a device
# snapshot (model, OS, storage, app usage last 24 h), photo GPS tags if present. Skips files already saved in earlier
# pulls of the same phone (name + size). Every file is checked against the phone's own SHA-256, then custody-logged.
# Shows the "please don't touch" progress page on the phone. Phone must be paired once (Developer options >
# Wireless debugging). The address comes from mDNS, because it changes when the cable comes out.
#
#   SINCE="2026-11-13 07:00" bash scripts/wifi/pnet_wifi_pull.sh <SERIAL> /path/to/backups/_phone_<name>_<SERIAL>_delta_ [port]
#
# WAIT_UNPLUG=1 waits up to 6 min for the USB cable to come out first, so the run is Wi-Fi only.
set -uo pipefail
SER=$1; PREFIX=$2; PORT=${3:-8807}
SINCE=${SINCE:?set SINCE="YYYY-MM-DD HH:MM"}
CUSTODY=${CUSTODY:-}   # optional: a script that logs one custody line per pull, called as: $CUSTODY acquire <SHA256SUMS.txt> device=<serial> ...
PY=${PY:-python3}
APP=${APP:-$(cd "$(dirname "$0")/../.." && pwd)}   # the phone-net-ICKS folder (for stack/jobboard/phone_status.py)
DAY=$(date +%F); P=${PREFIX}${DAY}_wifi; k=1; while [ -e "$P" ]; do k=$((k+1)); P=${PREFIX}${DAY}_wifi$k; done; mkdir -p "$P"
L=$P/PULL_LOG.txt; ts(){ date '+%F %T'; }; EP=$(date -j -f '%Y-%m-%d %H:%M' "$SINCE" +%s)

if [ "${WAIT_UNPLUG:-0}" = 1 ]; then
  for i in $(seq 1 90); do adb devices | grep -q "^$SER[[:space:]]" || break; sleep 4; done
  adb devices | grep -q "^$SER[[:space:]]" && { echo "cable still in after 6 min; stopping"; exit 1; }
  sleep 4
fi
W=""; for i in $(seq 1 15); do
  W=$(adb mdns services 2>&1 | grep "adb-$SER-" | awk '{print $3}' | tail -1)
  [ -n "$W" ] && { adb devices | grep -q "^$W[[:space:]]*device" || timeout 15 adb connect "$W" >/dev/null 2>&1; }
  [ -n "$W" ] && adb devices | grep -q "^$W[[:space:]]*device" && break; sleep 4; done
if [ -z "$W" ] || ! adb devices | grep -q "^$W[[:space:]]*device"; then   # mDNS can drop a phone that is still connected
  for d in $(adb devices | awk 'NR>1 && $2=="device" && $1 ~ /:/ {print $1}'); do
    [ "$(adb -s "$d" shell getprop ro.serialno </dev/null 2>/dev/null | tr -d '\r')" = "$SER" ] && { W=$d; break; }; done
fi
[ -n "$W" ] || { echo "phone $SER not found on Wi-Fi (is Wireless debugging on?)"; exit 1; }
A=(adb -s "$W"); echo "wifi target $W"

{ echo "$(ts) phase1 start $SER over Wi-Fi ($W) since $SINCE -> $P"; echo "$(ts) phone connected"; echo "$(ts) unlocked"; } > "$L"
( cd "$APP" && nohup "$PY" stack/jobboard/phone_status.py --root "$P" --port "$PORT" \
    --title "Wi-Fi pull · please don't touch" --next "✅ Copy finished over Wi-Fi. You can use the phone again." >/dev/null 2>&1 </dev/null & )
sleep 2; "${A[@]}" reverse tcp:$PORT tcp:$PORT </dev/null >/dev/null 2>&1
"${A[@]}" shell "am start -a android.intent.action.VIEW -d http://localhost:$PORT" </dev/null >/dev/null 2>&1

# 1) messages and calls since SINCE (bodies stay in local files; counts go to the log)
"${A[@]}" shell "content query --uri content://sms --projection date:type:address:body --where 'date>${EP}000'" </dev/null > "$P/SMS_since.local.txt" 2>&1
"${A[@]}" shell "content query --uri content://mms --projection _id:date:msg_box --where 'date>${EP}'" </dev/null > "$P/MMS_INDEX_since.local.txt" 2>&1
"${A[@]}" shell "content query --uri content://call_log/calls --projection date:duration:type:number:name --where 'date>${EP}000'" </dev/null > "$P/CALL_LOG_since.local.txt" 2>&1
for f in SMS MMS_INDEX CALL_LOG; do echo "$(ts) content://$f rows=$(grep -c '^Row' "$P/${f}_since.local.txt")" >> "$L"; done

# 2) device snapshot: model, OS, storage, battery, app usage (last 24 h, package names and minutes only)
{ echo "model=$("${A[@]}" shell getprop ro.product.model </dev/null | tr -d '\r')"
  echo "android=$("${A[@]}" shell getprop ro.build.version.release </dev/null | tr -d '\r')"
  echo "build=$("${A[@]}" shell getprop ro.build.display.id </dev/null | tr -d '\r')"
  "${A[@]}" shell 'df -h /storage/emulated | tail -1' </dev/null | tr -d '\r' | awk '{print "storage_size="$2" free="$4" used="$5}'
  "${A[@]}" shell 'dumpsys battery | grep -E " level| temperature| health"' </dev/null | tr -d '\r' | sed 's/^ *//'
} > "$P/DEVICE_SNAPSHOT.txt" 2>&1
"${A[@]}" shell 'dumpsys usagestats --hours 24 2>/dev/null' </dev/null | tr -d '\r' \
  | grep -o -E 'package=[a-zA-Z0-9_.]+ totalTimeUsed="[^"]*"' | sort -u > "$P/APP_USAGE_24h.local.txt" 2>/dev/null
echo "$(ts) device snapshot + app usage saved" >> "$L"

# 3) media newer than SINCE on internal + SD, minus files already saved for this phone (name + size)
VOLS="/sdcard/DCIM /sdcard/Movies /sdcard/Pictures /sdcard/Recordings /sdcard/Music /sdcard/Download /sdcard/Documents $("${A[@]}" shell 'ls -d /storage/*-*/DCIM /storage/*-*/Music /storage/*-*/Recordings 2>/dev/null' </dev/null | tr -d '\r' | tr '\n' ' ')"
"${A[@]}" shell "find $VOLS -type f -newermt '$SINCE' \( -iname '*.mp4' -o -iname '*.mov' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.heic' -o -iname '*.png' -o -iname '*.m4a' -o -iname '*.mp3' -o -iname '*.wav' -o -iname '*.amr' -o -iname '*.3gp' -o -iname '*.pdf' \) -exec stat -c '%s|%n' {} + 2>/dev/null" </dev/null \
  | tr -d '\r' | sort -t'|' -k2 > "$P/_pull_list.txt"
find ${PREFIX%delta_}* -type f ! -path "$P/*" -exec stat -f '%z|%N' {} + 2>/dev/null | awk -F'|' '{n=split($2,a,"/"); print $1"|"a[n]}' | sort -u > "$P/_prior.txt"
: > "$P/_new.txt"; while IFS='|' read -r sz p; do grep -qxF "$sz|$(basename "$p")" "$P/_prior.txt" || echo "$sz|$p" >> "$P/_new.txt"; done < "$P/_pull_list.txt"
TOT=$(wc -l < "$P/_new.txt" | tr -d ' '); BYTES=$(awk -F'|' '{s+=$1} END{print s+0}' "$P/_new.txt")
echo "$(ts) new files 0/$TOT" >> "$L"
t0=$(date +%s); n=0
while IFS='|' read -r sz p; do mkdir -p "$P$(dirname "$p")"
  "${A[@]}" pull -a "$p" "$P$p" </dev/null >/dev/null 2>>"$P/_pull_err.txt" && n=$((n+1)); echo "$(ts) new files $n/$TOT" >> "$L"
done < "$P/_new.txt"; t1=$(date +%s)

# 4) photo GPS tags (only if the camera saved them)
: > "$P/PHOTO_GPS.tsv"
while IFS='|' read -r sz p; do case "$p" in *.jpg|*.jpeg|*.JPG|*.heic)
  g=$(mdls -raw -name kMDItemLatitude -name kMDItemLongitude "$P$p" 2>/dev/null | tr '\0' ' ')
  case "$g" in *null*|"") ;; *) printf "%s\t%s\n" "$(basename "$p")" "$g" >> "$P/PHOTO_GPS.tsv";; esac;; esac
done < "$P/_new.txt"

# 5) checksums against the phone, custody
ok=0; bad=0
if [ "$TOT" -gt 0 ]; then
  (cd "$P" && find . -type f ! -name '_*' ! -name 'PULL_LOG.txt' ! -name 'SHA256SUMS.txt' ! -name '*.local.txt' ! -name 'DEVICE_SNAPSHOT.txt' ! -name 'PHOTO_GPS.tsv' -print0 | xargs -0 shasum -a 256 > SHA256SUMS.txt)
  while IFS='|' read -r sz p; do h=$("${A[@]}" shell "sha256sum '$p'" </dev/null | cut -c1-64); l=$(shasum -a 256 "$P$p" | cut -c1-64)
    if [ -n "$h" ] && [ "$h" = "$l" ]; then ok=$((ok+1)); else bad=$((bad+1)); echo "DIFF or MISSING $p" >> "$P/_pull_err.txt"; fi; done < "$P/_new.txt"
  [ -n "$CUSTODY" ] && bash "$CUSTODY" acquire "$P/SHA256SUMS.txt" device="$SER" source="phone (since $SINCE)" note="Wi-Fi pull (adb wireless)" >/dev/null 2>&1
fi
if [ "$n" -eq "$TOT" ] && [ "$bad" -eq 0 ]; then echo "$(ts) phase1 done · SAFE TO UNPLUG: $n of $TOT copied over Wi-Fi, checksums $ok match" >> "$L"
else echo "$(ts) INCOMPLETE: $n of $TOT copied, $ok verified, $bad missing or different. Rerun the same command to finish (it skips what is saved)." >> "$L"; fi
# let the finish screen show, then stop this pull's progress page so the script can exit
( sleep 30; pkill -f "phone_status.py --root $P " ) >/dev/null 2>&1 </dev/null &
secs=$((t1-t0)); [ $secs -lt 1 ] && secs=1
echo "WIFI_PULL $SER: $n/$TOT files, $(awk -v b=$BYTES 'BEGIN{printf "%.1f",b/1048576}') MB in ${secs}s; checksums $ok ok, $bad differ; sms $(grep -c '^Row' "$P/SMS_since.local.txt"), mms $(grep -c '^Row' "$P/MMS_INDEX_since.local.txt"), calls $(grep -c '^Row' "$P/CALL_LOG_since.local.txt"); photos with GPS $(wc -l < "$P/PHOTO_GPS.tsv" | tr -d ' ') -> $P"
