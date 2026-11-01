#!/usr/bin/env bash
# Full raw pull of an Android phone (adb) and then an iOS device (unencrypted full backup),
# for local-only parsing. No message bodies are printed; everything lands on local disk.
#
#   bash scripts/memorial_device_recon_pull.sh <dest_root> [adb_serial]
#
# Phase 1 (Android): /sdcard tree, SMS, MMS (+ every MMS part binary), call log, contacts,
#   calendar, app usage stats, package install times, accounts.
# Phase 2 (iOS): waits for an iPad/iPhone on USB, pairs (tap Trust on the device),
#   checks backup encryption is OFF, runs `idevicebackup2 backup --full`.
set -uo pipefail
ROOT=${1:?dest root}; SERIAL=${2:-$(adb devices | awk 'NR>1&&$2=="device"{print $1;exit}')}
[ "$SERIAL" = "ios" ] && SERIAL=""   # ios = skip the Android phase
LOG="$ROOT/PULL_LOG.txt"; mkdir -p "$ROOT"; exec >>"$LOG" 2>&1
ts(){ date '+%F %T'; }

if [ -n "$SERIAL" ]; then
  A=(adb -s "$SERIAL"); model=$("${A[@]}" shell getprop ro.product.model | tr -d '\r')
  D="$ROOT/android_${model}_${SERIAL}"; mkdir -p "$D/content" "$D/sdcard" "$D/mms_parts" "$D/system"
  echo "$(ts) phase1 start $model $SERIAL -> $D"
  for u in sms mms mms/part call_log/calls com.android.contacts/data com.android.contacts/raw_contacts \
           com.android.calendar/events com.android.calendar/calendars; do
    f="$D/content/$(echo "$u" | tr '/.' '__').txt"
    "${A[@]}" shell content query --uri "content://$u" > "$f" 2>&1
    echo "$(ts) content://$u rows=$(grep -c '^Row' "$f")"
  done
  # MMS part binaries (photos, video, audio, text) by part id
  grep -oE '^Row: [0-9]+ _id=[0-9]+' "$D/content/mms_part.txt" | awk -F= '{print $2}' | while read -r id; do
    [ -s "$D/mms_parts/$id.bin" ] && continue   # resume: keep parts already saved
    "${A[@]}" exec-out content read --uri "content://mms/part/$id" > "$D/mms_parts/$id.bin" 2>/dev/null
    [ -s "$D/mms_parts/$id.bin" ] || rm -f "$D/mms_parts/$id.bin"
  done
  echo "$(ts) mms part binaries=$(ls "$D/mms_parts" | wc -l)"
  # shared storage, one top-level dir at a time so a denied dir does not stop the rest
  for d in $("${A[@]}" shell ls /storage/emulated/0/ | tr -d '\r'); do
    "${A[@]}" pull -a "/storage/emulated/0/$d" "$D/sdcard/" >/dev/null 2>&1 || echo "$(ts) partial pull: $d"
  done
  echo "$(ts) sdcard pulled $(du -sh "$D/sdcard" | cut -f1)"
  "${A[@]}" shell dumpsys usagestats > "$D/system/usagestats.txt" 2>&1
  "${A[@]}" shell dumpsys package packages | grep -E 'Package \[|firstInstallTime|lastUpdateTime' > "$D/system/package_times.txt" 2>&1
  "${A[@]}" shell pm list packages -3 > "$D/system/packages_user.txt" 2>&1
  "${A[@]}" shell dumpsys account > "$D/system/accounts.txt" 2>&1
  "${A[@]}" shell getprop > "$D/system/getprop.txt" 2>&1
  echo "$(ts) phase1 done"
fi

# Phase 2: iOS
I="$ROOT/ios_backup"; mkdir -p "$I"
echo "$(ts) phase2 waiting for iOS device (plug in, unlock, tap Trust)"
until [ -n "$(idevice_id -l 2>/dev/null)" ]; do sleep 20; done
U=$(idevice_id -l | head -1); echo "$(ts) iOS device $U"
until idevicepair -u "$U" validate >/dev/null 2>&1; do idevicepair -u "$U" pair >/dev/null 2>&1; sleep 15; done
ideviceinfo -u "$U" -k DeviceName; ideviceinfo -u "$U" -k ProductType; ideviceinfo -u "$U" -k ProductVersion
enc=$(ideviceinfo -u "$U" -q com.apple.mobile.backup -k WillEncrypt 2>/dev/null)
echo "$(ts) WillEncrypt=$enc"
if [ "$enc" = "true" ]; then echo "$(ts) STOP: backup encryption is ON on the device; need the old password to turn it off"; exit 2; fi
idevicebackup2 -u "$U" backup --full "$I"; rc=$?
echo "$(ts) phase2 done rc=$rc size=$(du -sh "$I" | cut -f1)"
