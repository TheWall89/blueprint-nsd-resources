#!/usr/bin/env bash
# Safe and short version of builtin options
set -euo pipefail

# Options short tutorial, remove if not necessary
#
# Exit on error. Append "|| true" if you expect an error. (-e)
# set -o errexit
# Do not allow use of undefined vars. Use ${VAR:-} to use an undefined VAR (-u)
# set -o nounset
# Catch the error in case mysqldump fails (but gzip succeeds) in `mysqldump |gzip` 
# set -o pipefail
# Exit on error inside any functions or subshells. (-E)
# set -o errtrace
# Turn on traces, useful while debugging but commented out by default
# set -o xtrace

# Set magic variables for current file & dir
__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
__file="${__dir}/$(basename "${BASH_SOURCE[0]}")"
__base="$(basename "${__file}" .sh)"
#__root="$(cd "$(dirname "${__dir}")" && pwd)" # <-- change this as it depends on your app

# defaults
VERBOSE=0
OPT_EXAMPLE=option_value

# Help command output
usage(){
  echo "
  ${__base}.sh [OPTION...]
  -h; Print this help and exit
  -v; Set verbose output
  -o <the_option>; Option to be set (default: ${OPT_EXAMPLE})
  " | column -t -s ";"
}

function log() {
  if [ "${VERBOSE}" = 1 ]; then
    echo -e "$(date --iso-8601='seconds') - $*"
  fi
}

while getopts ":hvo:" opt; do
  case ${opt} in
    h )
      usage
      exit 0
      ;;
    v )
      VERBOSE=1
      ;;
    o )
      OPT_EXAMPLE=${OPTARG}
      ;;
    \? )
      usage
      exit 2
      ;;
  esac
done
shift $((OPTIND-1))

log "opt example: $OPT_EXAMPLE"

# Your code here
for f in */*;
do
  if [[ ${f} =~ ^.+(vsb|VSB).*(yml|yaml)$ ]]; then
    log "processing $f";
    json=$(yq . "$f")
    log "$json"
  fi
done
