# WARNING: This script takes a long time to execute if you have a high count
#          of active servers.
# Authors: Leslie Devlin and Sean Nicholson
# Version 1.0.0
# Date 05.25.2017
##############################################################################

# Import Python Modules
import json, csv, base64, requests, os, argparse
import cloudpassage
import yaml
import time
from time import sleep
global api_session

# Set variable types
user_credential_b64 = ''
headers = {}
api_key_description = ''


# Define Methods
def create_api_session(session):
    config_file_loc = "cloudpassage.yml"
    config_info = cloudpassage.ApiKeyManager(config_file=config_file_loc)
    session = cloudpassage.HaloSession(config_info.key_id, config_info.secret_key)
    return session


# Create headers
def get_headers():
    with open('cloudpassage.yml') as config_settings:
        api_info = yaml.load(config_settings)
        api_key_token = api_info['defaults']['key_id'] + ":" + api_info['defaults']['secret_key']
        api_request_url = "https://" + api_info['defaults']['api_hostname'] + ":443"
    user_credential_b64 = "Basic " + base64.b64encode(api_key_token)
    reply = get_access_token(api_request_url, "/oauth/access_token?grant_type=client_credentials",
                             {"Authorization": user_credential_b64})
    reply_clean = reply.encode('utf-8')
    headers = {"Content-type": "application/json", "Authorization": "Bearer " + reply_clean}
    return headers



# Request Bearer token and return access_token
def get_access_token(url, query_string, headers):
    retry_loop_counter = 0
    while retry_loop_counter < 5:
        reply = requests.post(url + query_string, headers=headers)
        if reply.status_code == 200:
            return reply.json()["access_token"]
            retry_loop_counter = 10
        else:
            retry_loop_counter += 1
            time.sleep(30)


# Query Halo API /v2/groups for root and subgroup names, IDs and totals
def get_halo_groups(session):
    get_halo_subgroups_list = cloudpassage.HttpHelper(session)
    with open('cloudpassage.yml') as config_settings:
        script_options_info = yaml.load(config_settings)
        root_group_id = script_options_info['defaults']['root_group_id']

# get account-wide totals
    get_root_totals=cloudpassage.HttpHelper(session)
    root_totals_reply=get_root_totals.get("/v2/groups/" + root_group_id)["group"]["aggregated_server_counts"]
    root_active=root_totals_reply['active']
    root_missing=root_totals_reply['missing']
    root_deactiv=root_totals_reply['deactivated']
    root_total=root_totals_reply['total']
    print "Root Group Totals:\n   Active: %s\n  Missing: %s\n  Deactivated: %s \
      \n  Total: %s\n\n" % ( root_active, root_missing, root_deactiv, \
     root_total )

# start report file
    out_file = "Halo_Server_Counts_Report_" + time.strftime("%Y%m%d") +".csv"
    ofile = open(out_file, "w")
    ofile.write('Group Name,Active,Missing,Deactivated,Group Total,Pct Active,Pct Total\n')
    root_row="Root Group,{0},{1},{2},{3},100,100\n".format(root_active,root_missing,root_deactiv,root_total)
    ofile.write(root_row)
    ofile.close()

# get subgroup data
    group_reply=get_halo_subgroups_list.get_paginated("/v2/groups?parent_id=" + root_group_id + "&per_page=100","groups",15)
    halo_subgroups_list=[]
    for group in group_reply:
        group_id=group['id']
        group_name=group['name']
        get_halo_data=cloudpassage.HttpHelper(session)
        subgroup_totals_reply = get_halo_data.get("/v2/groups/" + group_id)["group"]["aggregated_server_counts"]
        subgroup_active=subgroup_totals_reply['active']
        subgroup_missing=subgroup_totals_reply['missing']
        subgroup_deactiv=subgroup_totals_reply['deactivated']
        subgroup_total=subgroup_totals_reply['total']
        subgroup_pct_active=(float(subgroup_active) / float(root_active))*100
        subgroup_pct_total=(float(subgroup_total) / float(root_total))*100

# write subgroup data to row
        ofile = open(out_file, "a")
        subgroup_row="{0},{1},{2},{3},{4},{5:.2f},{6:.2f}\n".format(group_name,subgroup_active,subgroup_missing,subgroup_deactiv,subgroup_total,subgroup_pct_active,subgroup_pct_total)
        ofile.write(subgroup_row)
        ofile.close()

	

if __name__ == "__main__":
    api_session = None
    api_session = create_api_session(api_session)
    get_headers()
    get_halo_groups(api_session)
