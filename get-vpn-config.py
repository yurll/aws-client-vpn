#!/usr/bin/env python
import argparse
import boto3
import glob
import logging
import os
import random
import string
import re

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

def randomString(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))

parser = argparse.ArgumentParser()
parser.add_argument("--verbose", help="increase output verbosity",
                    action="store_true")

parser.add_argument("--name", help="stack and environment name the vpn",
                    action="store", required=True)

parser.add_argument("--region", help="aws region the vpn exists",
                    action="store", required=False)

args = parser.parse_args()
print("DEBUG: args.region: ", args.region)

if not args.region:
    try:
        args.region = os.environ['AWS_REGION']
    except KeyError as ex:
        log.error('Set the aws region using --region or environment variable AWS_REGION')
        exit(1)
if args.verbose:
    log.setLevel(logging.DEBUG)
    log.debug('set log level to verbose')

client = boto3.client('ec2', region_name=args.region)

server_name = f"{args.name}"
server = client.describe_client_vpn_endpoints(
    MaxResults=5,
    Filters=[
        {
            'Name': 'tag:Name',
            'Values': [server_name]
        }
    ]
)

if server['ClientVpnEndpoints']:
    id = server['ClientVpnEndpoints'][0]['ClientVpnEndpointId']
else:
    log.error(f"Unable to find client vpn {args.name}")
    exit(1)

vpn_config = client.export_client_vpn_client_configuration(
    ClientVpnEndpointId=id
)

config = vpn_config['ClientConfiguration']
config = re.sub(rf"{id}.*",rf"{randomString()}.{id}.prod.clientvpn.{args.region}.amazonaws.com 443",config)

client_cert_file = glob.glob(f'output/*{args.name}*.crt')[0]
with open(client_cert_file, 'r') as file:
    client_cert_file_content = file.read()
regex = re.compile(r'-----BEGIN CERTIFICATE-----.*', re.S)
client_cert = regex.search(client_cert_file_content).group(0)
config = config + f"<cert>\n{client_cert}\n</cert>\n"

client_key_file = glob.glob(f'output/*{args.name}*.key')[0]
with open(client_key_file, 'r') as file:
    client_key_file_content = file.read()
config = config + f"<key>\n{client_key_file_content}\n</key>\n"


config_file = f"output/{id}.ovpn"
with open(config_file, 'w') as file:
    file.write(config)

log.info(f"Created config file {config_file}")
log.info("Please copy the config along with the client certificate a key to a secure location in your computer")
log.info("Modify cert and key values of the new certificate and key file locations")
log.info(f"Run `open {config_file}` from the config file location to import the config tunnelblick or openvpn client")
