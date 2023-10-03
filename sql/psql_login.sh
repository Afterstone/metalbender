# Usage:
#  ./psql_login.sh <db> <username> <password>
#  ./psql_login.sh usage_monitor usage_monitor_user <password>
#
# NB!!! Run the command with a space in front to avoid storing the command in bash history.

psql "dbname=$1 user=$2 password=$3 host=34.90.150.50 sslmode=verify-ca sslcert=certs/client-cert.pem sslkey=certs/client-key.pem sslrootcert=certs/server-ca.pem"