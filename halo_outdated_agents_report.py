# WARNING: This script takes a long time to execute if you have a high count
#          of active servers.
# Authors: Leslie Devlin and Sean Nicholson
# Version 1.0.0
# Date 05.17.2017
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


# Query Halo API /v1/groups to get list of groups to generate reports for
def get_halo_groups(session):
    old_agent_count = 0
    if not os.path.exists("reports"):
          os.makedirs("reports")
    get_halo_groups_list = cloudpassage.HttpHelper(session)
    with open('cloudpassage.yml') as config_settings:
        script_options_info = yaml.load(config_settings)
        root_group_id = script_options_info['defaults']['root_group_id']
    group_reply=get_halo_groups_list.get_paginated("/v2/groups?parent_id=" + root_group_id + "&descendants=true","groups",15)
    halo_group_id_list=[]
    halo_server_id_list=[]
    for group in group_reply:
        halo_group_id_list.append({'group_id':group['id'], 'group_name': group['name']})
        group_id = group['id']
        group_name = group['name']
        # print "Group %s is %s" % (group_name, group_id)

        # create report file
        out_file = "reports/Agents_Report_" + group_name + "_" + time.strftime("%Y%m%d") + ".csv"
        ofile  = open(out_file, "w")
        get_halo_servers_list = cloudpassage.HttpHelper(session)
        servers_reply=get_halo_servers_list.get_paginated("/v2/servers?group_id=" + group_id + "&state=active&agent_version_lt=3.9.7&descendants=true","servers",30)
        ofile.write('Hostname,Halo Agent Version,Agent Started At,OS Name,OS Version,OS Distribution,OS Architecture,OS Service Pack,Group Name,Group ID\n')
        # count servers - if 0, then remove file
        server_count=0
        for server in servers_reply:
            if server:
                row="'{0}',{1},{2},{3},{4},{5},{6},{7},{8},{9}\n".format(server['hostname'],server['agent_version'],server['agent_started_at'],server['os_name'],server['os_version'],server['os_distribution'],server['os_architecture'],server['os_servicepack'],server['group_name'],server['group_id'])
                # print row
                server_count += 1
                ofile.write(row)
                ofile.close()
        if server_count == 0:
            os.remove(out_file)
            # print "No outdated agents present. File %s removed.\n" % out_file

#    halo_group_id_list = byteify(halo_group_id_list)
#    print halo_group_id_list
#    return halo_group_id_list



if __name__ == "__main__":
    api_session = None
    api_session = create_api_session(api_session)
    get_headers()
    get_halo_groups(api_session)
