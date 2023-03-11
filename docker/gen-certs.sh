#!/bin/bash

R='\033[0;31m'   #'0;31' is Red's ANSI color code
G='\033[0;32m'   #'0;32' is Green's ANSI color code
Y='\033[1;33m'   #'1;33' is Yellow's ANSI color code
B='\033[0;34m'   #'0;34' is Blue's ANSI color code
NC='\033[0m' # No Color

if [ "$EUID" -ne 0 ]; then
  echo -e "${R}Please run as root${NC}"
  exit 1
fi

if [ "$1" == "" ]; then
  echo -e "${R}Error: Must provide the user${NC}"
  exit 1
fi

MY="/etc/ssl/certs/`hostname -s`-"

EXISTING=`ls -1 ${MY}* 2>/dev/null`

if [ "${EXISTING}" == "" ]; then
  echo -e "${B}Generating certificates and keys using ${MY} as base${NC}"

  echo -e "${B}Generating self signed root CA cert ${MY}ca.key and ${MY}ca.crt${NC}"
  openssl req -nodes -x509 -newkey rsa:2048 -keyout ${MY}ca.key -out ${MY}ca.crt \
  -subj "/C=IT/ST=Lazio/L=Rome/O=K-Tech/OU=root/CN=`hostname -s`/emailAddress=noreply@k-tech.it"


  echo -e "${B}Generating server cert to be signed ${MY}server.key and ${MY}server.csr${NC}"
  openssl req -nodes -newkey rsa:2048 -keyout ${MY}server.key -out ${MY}server.csr \
   -subj "/C=IT/ST=Lazio/L=Rome/O=K-Tech/OU=root/CN=`hostname -s`/emailAddress=noreply@k-tech.it"

  #
  echo -e "${B}Sign the server cert ${MY}server.crt${NC}"
  openssl x509 -req -in ${MY}server.csr -CA ${MY}ca.crt -CAkey ${MY}ca.key -CAcreateserial -out ${MY}server.crt

  echo -e "${B}Create server PEM file ${MY}server.pem${NC}"
  cat ${MY}server.key ${MY}server.crt > ${MY}server.pem


  echo -e "${B}Generate client cert to be signed ${MY}client.key and ${MY}client.csr${NC}"
  openssl req -nodes -newkey rsa:2048 -keyout ${MY}client.key -out ${MY}client.csr \
  -subj "/C=IT/ST=Lazio/L=Rome/O=K-Tech/OU=root/CN=`hostname -s`/emailAddress=noreply@k-tech.it"

  # Sign the client cert
  echo -e "${B}Sign the client cert ${MY}client.crt${NC}"
  openssl x509 -req -in ${MY}client.csr -CA ${MY}ca.crt -CAkey ${MY}ca.key -CAserial ${MY}ca.srl -out ${MY}client.crt

  echo -e "${B}Create client PEM file ${MY}client.pem${NC}"
  cat ${MY}client.key ${MY}client.crt > ${MY}client.pem

  echo -e "${G}List of files generated:"
  ls -l ${MY}*
  echo -e "${NC}"

else
  ls -l ${MY}*

  while true; do
    echo -n -e "${Y}Do you want to soft link ${MY}server.key and ${MY}server.crt in certs folder?${NC} "
    read yn
    case $yn in
        [Yy]* ) ln -s ${MY}server.key certs/server.key && ln -s ${MY}server.crt certs/server.crt && chown $1 certs/server* && ls -lart certs/;  break;;
        [Nn]* ) exit;;
        * ) echo -e "${R}Please answer yes or no.${NC}";;
    esac
done
fi
