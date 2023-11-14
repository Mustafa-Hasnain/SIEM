from django.shortcuts import render, redirect
import requests
from django.http import JsonResponse, HttpResponse
from django.conf import settings
import json
from rest_framework.decorators import api_view
from io import BytesIO
import base64
import matplotlib
matplotlib.use('Agg')  # Use the Agg backend
import matplotlib.pyplot as plt
from asgiref.sync import async_to_sync
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from collections import Counter
import networkx as nx
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from xhtml2pdf import pisa
from django.template.loader import get_template
# Create your views here.

def index(request):
    return render(request, 'index.html')

def create_elasticsearch_index(request):
    url = f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}/testing_indices"
    print(str(url))
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': settings.ELASTICSEARCH_API_KEY,
    }
    
    response = requests.put(url, headers=headers)
    
    if response.status_code == 200:
        return JsonResponse({'message': 'Elasticsearch index created successfully'})
    else:
        return JsonResponse({'message': 'Failed to create Elasticsearch index'}, status=500)
    
@api_view(['POST'])    
def index_data_to_elastic_search(request):
    try:
        # Parse the JSON data from the request body
        data = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'message': 'Invalid JSON data in the request body'}, status=400)

        # Define the Elasticsearch URL for the specific index where you want to add a document
    index_url = f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}/testing_indices/_doc"
    headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': settings.ELASTICSEARCH_API_KEY,
        }

    try:
        response = requests.post(index_url, headers=headers, json=data)
        if response.status_code == 201:
            return JsonResponse({'message': 'Document indexed successfully in Elasticsearch'})
        else:
            return JsonResponse({'message': 'Failed to index document in Elasticsearch'}, status=500)
    except Exception as e:
        return JsonResponse({'message': f'Error: {str(e)}'}, status=500)

@api_view(['GET']) 
def getIOCS(request):
    
    print("Inside Function")
    #return JsonResponse({'msg':'testing the route...'})
    misp_url = 'https://192.168.17.17'
    misp_key = 'PsXjjrhWDhSmXeuSvIpGYZ84acLPO0quAPKeihnl'

    search_params = {
    #"eventid": 1,
    "returnFormat": "json"
    }

    print(search_params)

    headers = {
        "Authorization": misp_key,
        "Content-Type": "application/json",
    }

    counter=0
    while True:
        print("Inside Loop")
        
        counter+=1
        search_params['eventid'] = counter
        response = requests.post(f"{misp_url}/attributes/restSearch", json=search_params, headers=headers, verify=False)
        if response.status_code == 200:
            response_data = response.json()
            attributes_data = response_data.get('response', {}).get('Attribute', [])
            
            for attribute in attributes_data:
                category = attribute.get('category')
                attr_type = attribute.get('type')
                value = attribute.get('value')
                event_id=attribute.get('event_id')
                print(f"Category: {category}, Type: {attr_type}, Value: {value}, Event ID: {event_id}")
                post_IOCS_to_elastic_search(category, attr_type, value, event_id)
        else:
            print(f"Failed to retrieve attributes. Status code: {response.status_code}")
            return JsonResponse({'result': 'Attributes finished ...'})
    
    return JsonResponse({'result': 'Completed fetching IOCS ...'})


def post_IOCS_to_elastic_search(category, attr_type, value, event_id):
    try:
        # Parse the JSON data from the request body
        data = {
            'category': category,
            'attr_type': attr_type,
            'value': value,
            'event_id': event_id
        }
    except json.JSONDecodeError:
        return JsonResponse({'message': 'Invalid JSON data in the request body'}, status=400)

        # Define the Elasticsearch URL for the specific index where you want to add a document
    index_url = f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}/iocs_index_data/_doc"
    headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': settings.ELASTICSEARCH_API_KEY,
        }

    try:
        response = requests.post(index_url, headers=headers, json=data)
        if response.status_code == 201:
            return JsonResponse({'message': 'Document indexed successfully in Elasticsearch'})
        else:
            return JsonResponse({'message': 'Failed to index document in Elasticsearch'}, status=500)
    except Exception as e:
        return JsonResponse({'message': f'Error: {str(e)}'}, status=500)

@async_to_sync
async def get_logs(date):
    elasticsearch_url = f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}/syslogs_index/_search"
    #elasticsearch_url = "https://62f0-43-246-221-81.ngrok-free.app/syslog_index/_search"
    #request_body = {"query": {"match": {"timestamp":date.isoformat()}},"size":500}
    request_body = {"query": {"match_all": {}},"size": 1000,"sort": [
    {
      "@timestamp": {
        "order": "desc"
      }
    }
  ]}
        # Convert the request body to JSON
    request_body_json = json.dumps(request_body)

    # Define the headers
    headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': settings.ELASTICSEARCH_API_KEY,
        }

    try:
        # Make a POST request to the Elasticsearch URL with the request body
        response = requests.post(elasticsearch_url, data=request_body_json, headers=headers)

        # Check if the request was successful (HTTP status code 200)
        if response.status_code == 200:
            # Print the response content (Elasticsearch search results)
            return response.json()
        else:
            print(f"Request failed with status code {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

    # async with aiohttp.ClientSession() as session:
    #     # Use the aiohttp.post method to make a POST request
    #     async with session.post(elasticsearch_url, data=request_body_json, headers=headers) as response:
    #         if response.status == 200:
    #             response_data = await response.json()
    #             return response_data
    #         else:
    #             print(f"Request failed with status code {response.status}")
    #             return None

# Get the current date
current_date = datetime.now().date()
json_logs = get_logs(current_date)
while True:
    json_logs = get_logs(current_date)
    
    if json_logs and json_logs.get('hits', {}).get('total', {}).get('value', 0) > 0:
        # Process the data
        break  # Exit the loop if data is found

    current_date -= timedelta(days=1)


async def main():
    a = await get_logs(current_date)  # Await the asynchronous function
if __name__ == "__main__":
    json_logs = main()


def get_counts():
    json_response = json_logs
    hits = json_response.get("hits")
    total_logs =  hits['total']['value']
    hits_2 = hits.get("hits")
    app_risk_counts = {"low": 0, "medium": 0, "elevated": 0}
    for doc in hits_2:
        try:
            app_risk = doc["_source"]["apprisk"]
            app_risk_counts[app_risk] += 1
        except:
            continue
    counts = {'total_logs':total_logs, 'app_risk_counts':app_risk_counts}
    return counts

def sample_graph(request):    
    counts = get_counts()
    print(counts)

    json_response = json_logs
    hits = json_response.get("hits")
    hits_2 = hits.get("hits")
    hits_2 = remove_underscores(hits_2)

    # pie_chart_1 = pie_chart_for_logid()
    pie_chart_1 = pie_chart_for_level()
    pie_chart_2 = pie_chart_for_devices()
    bar_chart = barchart_3d()
    pie_chart_3 = pie_chart_for_devics_names()
    action_barchart = action_BarChart()
    
    return render(request,'index.html',{'pie_chart':pie_chart_1,'pie_chart_script':pie_chart_2,'bar_chart':f'data:image/png;base64,{bar_chart}','pie_chart_3_script':pie_chart_3,'total_logs':counts['total_logs'],'app_risks_total':counts['app_risk_counts'],'recent_logs':hits_2[:5],'action_BarChart':action_barchart})

def all_logs(request):
    json_response = json_logs
    hits = json_response.get("hits")
    hits_2 = hits.get("hits")
    hits_2 = remove_underscores(hits_2)
    return render(request, 'all_logs.html', {'logs':hits_2})

def log_detail(request, id):
    detail = get_log_detail(id)
    data = detail['_source']
     # Define field-to-section mapping
    field_sections = {
        'General': ['date', 'time', 'sessionid', 'logid', 'eventtime', 'level', 'policytype', 'path', 'device'],
        'Source': ['srcip', 'srcport', 'srcname', 'srcfamily', 'srcswversion', 'srcintf', 'srcintfrole', 'srchwvendor', 'srcuuid', 'srcmac'],
        'Destination': ['dstip', 'dstport', 'dstcountry', 'dstuuid', 'dstintf', 'dstintfrole'],
        'Application Control': ['appid', 'app', 'apprisk', 'osname', 'applist', 'appcat'],
        'Packets/Bytes': ['sentpkt', 'rcvdpkt', 'sentbyte', 'rcvdbyte'],
        'Other': [],  # For fields not mapped to any specific section
    }
     # Initialize sections for mapped fields and an "Other" section for unmapped fields
    sections = {section: {} for section in field_sections}

    # Sort fields into their respective sections
    for field, value in data.items():
        field_mapped = False
        for section, section_fields in field_sections.items():
            if field in section_fields:
                sections[section][field] = value
                field_mapped = True
                break
        if not field_mapped:
            sections['Other'][field] = value
    # print(sections)
    return render(request, 'log_detail.html',{'sections':sections})

def search_form(request):
    if request.method == 'POST':
        page=1
        ip = request.POST.get("ip")
        mac = request.POST.get("mac")
        machine_name = request.POST.get("machine_name")
        log_id = request.POST.get("log_id")
        asset_name = request.POST.get("asset_name")
        port = request.POST.get("port")
        level = request.POST.get("level")
        risk_level = request.POST.get("risk_level")
        PAGE_SIZE = 10000
        from_record = (page - 1) * PAGE_SIZE

        request_body = {"srcip": ip, "srcmac":mac, "src_name":machine_name, 
                        "log_id":log_id,"srcintf":port,"level":level,
                        "apprisk":risk_level
                        }
        # Initialize an empty list to store individual match queries
        match_queries = []
        for field, value in request_body.items():
            if value != "" :
                match_query = {
                    "match": {
                        field: value
                    }
                }
                match_queries.append(match_query)

        # Construct the Elasticsearch request body
        request_body = {
            "size":PAGE_SIZE,
            "query": {
                "bool": {
                    "must": match_queries
                }
            },
            "sort":[
                {
                    "@timestamp":{
                        "order":"desc"
                    }
                }
            ]
        }
        print(request_body)
        request.session["request_body"] = request_body
        try:
            del request.session['result_list']
        except:
            None
        return redirect(search_logs)
    
    return render(request, 'assets.html') 


def search_logs(request,page=1):
    PAGE_SIZE = 1000
    from_record = (page - 1) * PAGE_SIZE
    to = from_record + 1000
    logs = request.session.get('result_list',None)
    if(logs is None):
            # Example usage
        # Define the Elasticsearch URL and request body
        print("get_logs")
        elasticsearch_url = "http://192.168.17.9:9200"
        request_body = request.session.get("request_body",None)
        # Convert the request body to JSON
        request_body_json = json.dumps(request_body)
        # Define the headers
        headers = {"Content-Type": "application/json",
                "Accept": "application/json",
            "Authorization":"ApiKey a0pMVzlZb0J5QUdFanR5dVRuSk46OXF1bUNZWnhURUthQUJrQmZLdWZnZw=="}
        logs = get_search_logs(request,elasticsearch_url,headers,request_body_json)
        request.session['result_list'] = logs
    total_logs = int(request.session.get("total_logs",0))
    total_pages = (total_logs + PAGE_SIZE - 1) // PAGE_SIZE
    print(total_logs,total_pages)
    # logs = remove_underscores(logs)
    return render(request, 'search_logs.html', {'result_data': logs[from_record:to],'total_logs':total_logs,'total_pages':total_pages,'current_page':page})

    

def get_search_logs(request,es_url, headers, query):
    result_list = []
    # Initial search request
    response = requests.post(f"{es_url}/syslogs_index/_search?scroll=1m", query, headers=headers)
    response_json = response.json()
    hits = response_json['hits']['hits']
    total_logs = response_json['hits']['total']['value']
    request.session['total_logs'] = total_logs
    if hits:
        result_list.extend(hits)

    scroll_id = response_json['_scroll_id']
    scroll_request_body = {
        "scroll": "1m",
        "scroll_id": scroll_id
    }
    scroll_request_body = json.dumps(scroll_request_body)

    # Keep scrolling until no more data is available
    while hits:
        response = requests.post(f"{es_url}/_search/scroll", scroll_request_body, headers=headers)
        response_json = response.json()
        hits = response_json['hits']['hits']

        if hits:
            result_list.extend(hits)

    # Clear the scroll
    requests.delete(f"{es_url}/_search/scroll/{scroll_id}")
    return result_list
    
    
def get_log_detail(id):
    elasticsearch_url = f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}/syslogs_index/_doc/{id}"
    #elasticsearch_url = f"https://62f0-43-246-221-81.ngrok-free.app/syslog_index/_doc/{id}"
    # Define the headers
    headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': settings.ELASTICSEARCH_API_KEY,
        }
    try:
        # Make a POST request to the Elasticsearch URL with the request body
        response = requests.get(elasticsearch_url, headers=headers)

        # Check if the request was successful (HTTP status code 200)
        if response.status_code == 200:
            # Print the response content (Elasticsearch search results)
            return response.json()
        else:
            print(f"Request failed with status code {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

def pie_chart_for_level():
    elasticsearch_url = f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}/syslogs_index/_search?scroll=1m"
    #elasticsearch_url = f"https://62f0-43-246-221-81.ngrok-free.app/syslog_index/_search"
    request_body = {"size": 10000, "query": {"bool": {"must": [{"terms": {"level": ["critical", "alert", "emergency","error"]}}]}},
    "sort": [
        {
        "@timestamp": {
            "order": "desc"
        }
        }
    ]
    }
    request_body = json.dumps(request_body)

    # Define the headers
    headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': settings.ELASTICSEARCH_API_KEY,
        }
    response = requests.post(elasticsearch_url,request_body, headers=headers)
    json_logs = response.json()
    json_response = json_logs
    hits = json_response.get("hits")
    hits_2 = hits.get("hits")
    logid_counts = {}
    for doc in hits_2:
        try:
            logid = doc["_source"]["level"]
            logid_counts[logid] = logid_counts.get(logid, 0) + 1
        except:
            continue

    # Create data for the pie chart
    logids = list(logid_counts.keys())
    counts = list(logid_counts.values())

    script = """
        var labels = %s;
        var data = %s;

        var ctx = document.getElementById('pie-chart').getContext('2d');
        var myPieChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: [
                        'red',
                        'blue',
                        'yellow',
                        'green',
                        'purple',
                        'orange',
                    ],
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    animateScale: true,
                },
                tooltips: {
                    enabled: true,
                    mode: 'single',
                },
            },
        });
        """ % (logids, counts)
    return script


def pie_chart_for_logid():
    json_response = json_logs
    hits = json_response.get("hits")
    hits_2 = hits.get("hits")
    # #logids = [doc["_source"]["logid"] for doc in hits_2]
    # #logid_counts = {}
    # #or
    logid_counts = {}
    for doc in hits_2:
        try:
            logid = doc["_source"]["logid"]
            logid_counts[logid] = logid_counts.get(logid,0) + 1
        except:
            continue

    # Create data for the pie chart
    logids = list(logid_counts.keys())
    counts = list(logid_counts.values())
    print(logids)
    print(counts)
    plt.figure(figsize=(8, 8))
    plt.pie(counts, labels=logids, autopct='%1.1f%%', startangle=140)
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

    # Display the pie chart
    plt.title("LogID Distribution")
    # Save the plot to a BytesIO object
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)

    # Convert the image to a base64 data URL
    image_data = base64.b64encode(buffer.read()).decode()
    plt.close()
    return image_data

# def pie_chart_for_logid():
#     json_response = json_logs
#     hits = json_response.get("hits")
#     hits_2 = hits.get("hits")
#     # #logids = [doc["_source"]["logid"] for doc in hits_2]
#     # #logid_counts = {}
#     # #or
#     logid_counts = {}
#     for doc in hits_2:
#         logid = doc["_source"]["logid"]
#         logid_counts[logid] = logid_counts.get(logid,0) + 1

#     # Create data for the pie chart
#     logids = list(logid_counts.keys())
#     counts = list(logid_counts.values())
#     print(logids)
#     print(counts)
#     plt.figure(figsize=(8, 8))
#     plt.pie(counts, labels=logids, autopct='%1.1f%%', startangle=140)
#     plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

#     # Display the pie chart
#     plt.title("LogID Distribution")
#     # Save the plot to a BytesIO object
#     buffer = BytesIO()
#     plt.savefig(buffer, format='png')
#     buffer.seek(0)

#     # Convert the image to a base64 data URL
#     image_data = base64.b64encode(buffer.read()).decode()
#     plt.close()
#     return image_data

def pie_chart_for_devices():
    json_response = json_logs
    hits = json_response.get("hits")
    hits_2 = hits.get("hits")
    logid_counts = {}
    for doc in hits_2:
        try:
            logid = doc["_source"]["srcip"]
            logid_counts[logid] = logid_counts.get(logid,0) + 1
        except:
            continue

    # Create data for the pie chart
    logids = list(logid_counts.keys())
    counts = list(logid_counts.values())
    print(counts)
    print(logids)
    # plt.figure(figsize=(8, 8))
    # plt.pie(counts, labels=logids, autopct='%1.1f%%', startangle=140)
    # plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    script = """
        var labels =  %s ;
        var values =  %s ;

        var data = [{
            labels: labels,
            values: values,
            type: 'pie'
        }];

        Plotly.newPlot('pie', data); 
        """% (logids, counts)
    return script

def barchart_3d():
    json_response = json_logs
    hits = json_response.get("hits")
    hits_2 = hits.get("hits")
    search_counts = {}
    for doc in hits_2:
        try:
            qname = doc["_source"]["qname"]
            search_counts[qname] = search_counts.get(qname, 0) + 1
        except:
            continue
    # Extract qnames and search counts for plotting
    qnames = list(search_counts.keys())
    counts = list(search_counts.values())

    # Create a 3D bar graph
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    x = range(len(qnames))
    y = [0] * len(qnames)
    z = counts

    ax.bar(x, z, y, zdir='y', color='b', alpha=0.7)

    # Customize labels
    ax.set_xlabel("Site Names")
    ax.set_ylabel("Zero Line")
    ax.set_zlabel("Search Count")
    ax.set_xticks(x)
    ax.set_xticklabels(qnames, rotation=45, ha="right")

    # Display the 3D bar graph
    plt.title("Search Count by Site (Sample Data)")
    plt.tight_layout()
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    # Convert the image to a base64 data URL
    image_data = base64.b64encode(buffer.read()).decode()
    plt.close()
    return image_data   

def pie_chart_for_devics_names():
    json_response = json_logs
    hits = json_response.get("hits")
    hits_2 = hits.get("hits")
    logid_counts = {}
    for doc in hits_2:
        try:
            logid = doc["_source"]["srcname"]
            logid_counts[logid] = logid_counts.get(logid,0) + 1
        except:
            continue

    # Create data for the pie chart
    logids = list(logid_counts.keys())
    counts = list(logid_counts.values())
    print(counts)
    print(logids)
    # plt.figure(figsize=(8, 8))
    # plt.pie(counts, labels=logids, autopct='%1.1f%%', startangle=140)
    # plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    script = """
        var labels =  %s ;
        var values =  %s ;

        var data = [{
            labels: labels,
            values: values,
            type: 'pie'
        }];

        Plotly.newPlot('pie_names', data); 
        """% (logids, counts)
    return script   

def action_BarChart():
    json_response = json_logs
    hits = json_response.get("hits")
    hits_2 = hits.get("hits")
    logid_counts = {}
    for doc in hits_2:
        try:
            logid = doc["_source"]["action"]
            logid_counts[logid] = logid_counts.get(logid,0) + 1
        except:
            continue

    # Create data for the pie chart
    logids = list(logid_counts.keys())
    counts = list(logid_counts.values())
    print(counts)
    print(logids)
    
    script = """
    var labels = %s;
    var data = %s;

    // Get the canvas element and its context
    var canvas = document.getElementById('action-BarChart');
    var ctx = canvas.getContext('2d');

    // Clear the canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Initialize the bar chart
    var myBarChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Log Counts',
                data: data,
                backgroundColor: [
                    'red',
                    'blue',
                    'yellow',
                    'green',
                    'purple',
                    'orange',
                ],
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    beginAtZero: true
                },
                y: {
                    beginAtZero: true
                }
            },
        },
    });
    """ % (json.dumps(logids), json.dumps(counts))

    return script



def remove_underscores(json_data):
    if isinstance(json_data, str):
        json_data = json.loads(json_data)

    def remove_underscores_recursive(data):
        if isinstance(data, dict):
            return {key.replace('_', ''): remove_underscores_recursive(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [remove_underscores_recursive(item) for item in data]
        else:
            return data

    result = remove_underscores_recursive(json_data)
    return result

def download_csv(request):
    json_data = request.session.get('result_list')
    data_for_frame = []
    for doc in json_data:
        source_data = doc.get('_source',{})
        source_data['_id'] = doc.get('_id',None)
        data_for_frame.append(source_data)
    df = pd.DataFrame(data_for_frame)
    response = HttpResponse(content_type='text/csv')
    file_name = "data.csv"  # Set the desired file name here
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'
    df.to_csv(response, index=False)
    return response

def search_graphs(request):
    json_data = request.session.get('result_list')
    bytes_chart = bar_chart_for_bytes(json_data)
    srcnames_chart = pie_chart_for_srcname(json_data)
    levels_by_ip = levels_generated_by_ip(json_data)
    levels_per_day = levels_generated_per_day(json_data)
    action_barchart = search_action_BarChart(json_data)
    dstcountry_chart = piechart_of_dstcountry(json_data)

    return render(request, 'search_graphs.html', {'bytes_chart':bytes_chart,'srcnames_chart':srcnames_chart,'levels_by_ip':levels_by_ip,'levels_per_day':levels_per_day,'action_barchart':action_barchart,'dstcountry_chart':dstcountry_chart})


def bar_chart_for_bytes(json_data):
    sendbytes_by_ip = {}
    rcvdbytes_by_ip = {}
    send = 0
    rcvd = 0
    for log in json_data:
        try:
            source_ip = log['_source']['srcip']
            sendbytes = log['_source']['sentbyte']
            rcvdbytes = log['_source']['rcvdbyte']

            sendbytes_by_ip[source_ip] = 0
            sendbytes_by_ip[source_ip] = sendbytes_by_ip[source_ip] + int(sendbytes)
            
            rcvdbytes_by_ip[source_ip] = 0
            rcvdbytes_by_ip[source_ip] = rcvdbytes_by_ip[source_ip] + int(rcvdbytes)

        except:
            continue
    
    print(sendbytes_by_ip, rcvdbytes_by_ip)
        # Extract unique source IPs
    source_ips = list(set(list(sendbytes_by_ip.keys()) + list(rcvdbytes_by_ip.keys())))
    # Sort source IPs for consistency in plotting
    source_ips.sort()
     # Convert data to JSON format
    sendbytes_data = json.dumps([sendbytes_by_ip[ip] for ip in source_ips])
    rcvdbytes_data = json.dumps([rcvdbytes_by_ip[ip] for ip in source_ips])
    source_ips_data = json.dumps(source_ips)

    # Create the Chart.js script
    script = f"""
    var source_ips = {source_ips_data};
    var sendbytes_data = {sendbytes_data};
    var rcvdbytes_data = {rcvdbytes_data};

    // Get the canvas element and its context
    var canvas = document.getElementById('bytes-chart');
    var ctx = canvas.getContext('2d');

    // Clear the canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Initialize the grouped bar chart
    var myChart = new Chart(ctx, {{
        type: 'bar',
        data: {{
            labels: source_ips,
            datasets: [{{
                label: 'Send Bytes',
                data: sendbytes_data,
                backgroundColor: 'rgba(255, 99, 132, 0.7)',
            }},
            {{
                label: 'Received Bytes',
                data: rcvdbytes_data,
                backgroundColor: 'rgba(54, 162, 235, 0.7)',
            }}],
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            scales: {{
                x: {{
                    beginAtZero: true
                }},
                y: {{
                    beginAtZero: true
                }}
            }},
        }},
    }});
    """

    return script

def pie_chart_for_srcname(json_data):
    logid_counts = {}
    
    for doc in json_data:
        try:
            logid = doc["_source"]["srcname"]
            logid_counts[logid] = logid_counts.get(logid, 0) + 1
        except:
            continue

    logids = list(logid_counts.keys())
    counts = list(logid_counts.values())

    # Convert data to JSON format
    logids_json = json.dumps(logids)
    counts_json = json.dumps(counts)

    # JavaScript script
    script = f"""
        var labels = {logids_json};
        var data = {counts_json};

        var ctx = document.getElementById('pie-chart-names').getContext('2d');
        var myPieChart = new Chart(ctx, {{
            type: 'pie',
            data: {{
                labels: labels,
                datasets: [{{
                    data: data,
                    backgroundColor: [
                        'red',
                        'blue',
                        'yellow',
                        'green',
                        'purple',
                        'orange',
                    ],
                }}],
            }},
            options: {{
                responsive: true,
            }},
        }});
    """
    return script

def levels_generated_by_ip(json_data):
    # Count the occurrences of each unique source IP and level combination
    log_counts = {}
    for log in json_data:
        try:
            source_ip = log["_source"]["srcip"]
            level = log["_source"]["level"]

            if source_ip not in log_counts:
                log_counts[source_ip] = {"critical": 0, "alert": 0, "warning": 0, "notice": 0, "information": 0}

            log_counts[source_ip][level] += 1
        except KeyError:
            continue

    # Extract unique source IPs
    source_ips = list(log_counts.keys())

    # Sort source IPs for consistency in plotting
    source_ips.sort()
    print(log_counts)
    # Create data for the bar chart
    critical_counts = [log_counts[ip]["critical"] for ip in source_ips]
    alert_counts = [log_counts[ip]["alert"] for ip in source_ips]
    warning_counts = [log_counts[ip]["warning"] for ip in source_ips]
    notice_counts = [log_counts[ip]["notice"] for ip in source_ips]
    information_counts = [log_counts[ip]["information"] for ip in source_ips]

    # Convert data to JSON format
    source_ips_json = json.dumps(source_ips)
    critical_counts_json = json.dumps(critical_counts)
    alert_counts_json = json.dumps(alert_counts)
    warning_counts_json = json.dumps(warning_counts)
    notice_counts_json = json.dumps(notice_counts)
    information_counts_json = json.dumps(information_counts)

    # JavaScript script
    script = f"""
        var source_ips = {source_ips_json};
        var critical_counts = {critical_counts_json};
        var alert_counts = {alert_counts_json};
        var warning_counts = {warning_counts_json};
        var notice_counts = {notice_counts_json};
        var information_counts = {information_counts_json};

        var ctx = document.getElementById('ip-level-chart').getContext('2d');
        var myChart = new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: source_ips,
                datasets: [{{
                    label: 'Critical',
                    data: critical_counts,
                    backgroundColor: 'red'
                }}, {{
                    label: 'Alert',
                    data: alert_counts,
                    backgroundColor: 'blue',
                    stack: 'stack'
                }}, {{
                    label: 'Warning',
                    data: warning_counts,
                    backgroundColor: 'yellow',
                    stack: 'stack'
                }}, {{
                    label: 'Notice',
                    data: notice_counts,
                    backgroundColor: 'orange',
                    stack: 'stack'
                }}, {{
                    label: 'Information',
                    data: information_counts,
                    backgroundColor: 'green',
                    stack: 'stack'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{
                        stacked: true
                    }},
                    y: {{
                        stacked: true
                    }}
                }}
            }}
        }});
    """
    return script

def levels_generated_per_day(json_data):
    timestamps = []
    levels = []

    # Extract timestamps and levels from the logs
    for log in json_data:
        try:
            timestamps.append(log['_source']['@timestamp'])
            levels.append(log['_source']['level'])
        except:
            continue
     # Create a DataFrame
    df = pd.DataFrame({'timestamp': pd.to_datetime(timestamps), 'level': levels})

    # Set the timestamp column as the DataFrame index
    df.set_index('timestamp', inplace=True)

    # Resample the data by day and count occurrences
    log_counts = df.resample('D')['level'].value_counts().unstack(fill_value=0)

    # Convert the DataFrame to a JSON string
    labels = log_counts.index.strftime('%Y-%m-%d').tolist()
    datasets = []

    # Define colors for each level
    level_colors = {
        'critical': 'red',
        'alert': 'blue',
        'warning': 'yellow',
        'notice': 'orange',
        'information': 'green',
    }

    for level in log_counts.columns:
        data = log_counts[level].tolist()
        datasets.append({
            'label': level.capitalize(),
            'data': data,
            'backgroundColor': level_colors.get(level, 'rgba(0, 0, 0, 0)'),  # Default to black if color not defined
            'borderColor': level_colors.get(level, 'rgba(0, 0, 0, 0)'),
            'borderWidth': 1,
            'stack': 'stack'
        })

    script = f"""
        var ctx = document.getElementById('level-per-day-chart').getContext('2d');
        var myChart = new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(labels)},
                datasets: {json.dumps(datasets)},
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{
                        stacked: true,
                    }},
                    y: {{
                        stacked: true,
                    }},
                }},
            }},
        }});
    """
    return script



def search_action_BarChart(json_data):
    logid_counts = {}
    for doc in json_data:
        try:
            logid = doc["_source"]["action"]
            logid_counts[logid] = logid_counts.get(logid,0) + 1
        except:
            continue

    # Create data for the pie chart
    logids = list(logid_counts.keys())
    counts = list(logid_counts.values())
    
    
    script = """
    var labels = %s;
    var data = %s;

    // Get the canvas element and its context
    var canvas = document.getElementById('search-action-BarChart');
    var ctx = canvas.getContext('2d');

    // Clear the canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Initialize the bar chart
    var myBarChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Log Counts',
                data: data,
                backgroundColor: [
                    'red',
                    'blue',
                    'yellow',
                    'green',
                    'purple',
                    'orange',
                ],
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    beginAtZero: true
                },
                y: {
                    beginAtZero: true
                }
            },
        },
    });
    """ % (json.dumps(logids), json.dumps(counts))
    return script

def piechart_of_dstcountry(json_data):
    logid_counts = {}
    for doc in json_data:
        try:
            logid = doc["_source"]["dstcountry"]
            logid_counts[logid] = logid_counts.get(logid,0) + 1
        except:
            continue

    # Create data for the pie chart
    logids = list(logid_counts.keys())
    counts = list(logid_counts.values())

    script = """
        var labels = %s;
        var data = %s;

        var ctx = document.getElementById('pie-chart-dstcountry').getContext('2d');
        var myPieChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: [
                        'red',
                        'blue',
                        'yellow',
                        'green',
                        'purple',
                        'orange',
                    ],
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    animateScale: true,
                },
                tooltips: {
                    enabled: true,
                    mode: 'single',
                },
            },
        });
        """ % (logids, counts)
    return script


def action_BarChart():
    json_response = json_logs
    hits = json_response.get("hits")
    hits_2 = hits.get("hits")
    logid_counts = {}
    for doc in hits_2:
        try:
            logid = doc["_source"]["action"]
            logid_counts[logid] = logid_counts.get(logid,0) + 1
        except:
            continue

    # Create data for the pie chart
    logids = list(logid_counts.keys())
    counts = list(logid_counts.values())
    print(counts)
    print(logids)
    
    script = """
    var labels = %s;
    var data = %s;

    // Get the canvas element and its context
    var canvas = document.getElementById('action-BarChart');
    var ctx = canvas.getContext('2d');

    // Clear the canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Initialize the bar chart
    var myBarChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Log Counts',
                data: data,
                backgroundColor: [
                    'red',
                    'blue',
                    'yellow',
                    'green',
                    'purple',
                    'orange',
                ],
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    beginAtZero: true
                },
                y: {
                    beginAtZero: true
                }
            },
        },
    });
    """ % (json.dumps(logids), json.dumps(counts))

    return script

@csrf_exempt
def download_pdf(request):
    # Get the HTML content of the div from the template
    template = get_template('graph_template.html')
    context = {'data': 'your_context_data_here'}  # Pass any context data needed for rendering the template
    html_content = template.render(context)

    # Create a PDF file
    pdf_file = open("output.pdf", "wb")
    pisa.CreatePDF(html_content, dest=pdf_file)
    pdf_file.close()

    # Serve the PDF for download
    with open("output.pdf", "rb") as pdf:
        response = HttpResponse(pdf.read(), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="graph.pdf"'
        return response  









