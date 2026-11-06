#!/bin/sh
# Every note under notes/ ends with the line "Checked."
status=0
for note in notes/*.txt; do
  [ -e "$note" ] || continue
  if [ "$(tail -n 1 "$note")" != "Checked." ]; then
    echo "FAIL: $note must end with the line 'Checked.'"
    status=1
  fi
done
exit $status
