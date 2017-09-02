#!/usr/bin/python
# coding: utf-8

import pandas as pd
import numpy as np
import urllib
from bs4 import BeautifulSoup
from torrequest import TorRequest

csv_input = 'CSV/HSN_TSN_BRAND_STATUS.csv'
csv_output = 'CSV/OUTPUT.csv'


def main():
    input_df = pd.read_csv(csv_input)
    for index, row in input_df.iterrows():
        if row.Status == 0:
            hsn, tsn, brand = str(int(row.HSN)).zfill(4), row.TSN.zfill(3), row.Brand
            try:
                with TorRequest() as tor:
                    brand_id, model_id, vehicle_id, vehicle_example = get_vehicle_infos(tor, hsn, tsn)
                    main_services_list = get_main_services(tor, hsn, tsn, brand_id, model_id, vehicle_id)
                    service_name, service_overview, km, model, prices, sqi, url = get_final_infos(tor, vehicle_example)
                    services_detailed = get_services_details(tor, sqi)
                    result = generate_results_dictionary(brand, hsn, tsn, model, main_services_list,
                                                         service_name, service_overview, km, min(prices),
                                                         max(prices), np.mean(prices), services_detailed, url)
                save_execution_status(result, input_df, index, status=1)
            except:
                result = generate_results_dictionary(brand, hsn, tsn, '/', '/', '/', '/', '/', '/', '/', '/', '/', '/')
                save_execution_status(result, input_df, index, status=2)


def get_vehicle_infos(tor, hsn, tsn):
    vehicles_payload = {
        'HSN': hsn,
        'TSN': tsn,
        'vendor': '0',
        'service': '17'
    }
    url = 'https://www.werkstars.de/api/vehicle/provide/vehicles?' + urllib.urlencode(vehicles_payload)
    response = tor.get(url).json()
    brand_id = response['brand']['id']
    model_id = response['model']['id']
    vehicle_id = response['vehicles'][0]['id']
    vehicle_example = response['vehicles'][0]
    return brand_id, model_id, vehicle_id, vehicle_example


def get_main_services(tor, hsn, tsn, brand_id, model_id, vehicle_id):
    main_services_payload = {
        'HSN': hsn,
        'TSN': tsn,
        'VIN': '',
        'vehicle': vehicle_id,
        'brand': brand_id,
        'model': model_id,
        'vendor': '0',
        'service': '17',
        'kilometerAge': '10000',
        'initialRegistrationDate': ''
    }
    url = 'https://www.werkstars.de/api/vehicle/provide/service-plans?' + urllib.urlencode(main_services_payload)
    response = tor.get(url).json()
    return '|||'.join([response['servicePlans'][elem]['title'] for elem in response['servicePlans']])


def get_final_infos(tor, vehicle):
    url_part_1 = str(vehicle['brand']['seoLinkLabel'])
    url_part_2 = str(vehicle['seoLinkLabel'])
    url_part_3 = str(vehicle['id'])
    url = 'https://www.werkstars.de/Berlin/Inspektion+' + url_part_1 + '-' + url_part_2 + '?&VID=' + url_part_3
    soup = BeautifulSoup(tor.get(url).text, "html.parser")
    service_name = soup.select('li.inspection')[0].find('h2').text
    service_overview = '|||'.join([' '.join([p.text for p in elem.select('p')]) for elem in [tr for tr in soup.select('li.inspection')][0].findAll(True, {'class':['head', 'public']})])
    km = soup.select('div.grid_5')[0].select('section.kilometerAge')[0].text
    model = soup.select('div.grid_5')[0].select('section.brand')[0].text
    sqi = str(soup.select('section.service-capacity')[0].get_attribute_list('data-sqi')[0])
    prices = [float(price.text.encode('ascii', 'ignore').strip().replace(',', '.')) for price in soup.select('p.price')]
    return service_name, service_overview, km, model, prices, sqi, url


def get_services_details(tor, sqi):
    url = 'https://www.werkstars.de/service-und-leistungsbeschreibung?SQI=' + sqi
    response = BeautifulSoup(tor.get(url).text, "html.parser")
    return '|||'.join([' '.join([p.text for p in tr.select('p')]) for tr in response.select('tr')])


def generate_results_dictionary(brand, hsn, tsn, model,
                                main_services_list, service_name, service_overview,
                                km, min_price, max_price, mean_price,
                                services_detailed, url):
    return pd.DataFrame([{
        'brand': brand,
        'hsn': hsn,
        'tsn': tsn,
        'model': model,
        'main_services': main_services_list,
        'service_name': service_name,
        'service_overview': service_overview,
        'km': km,
        'min_price': min_price,
        'max_price': max_price,
        'mean_price': mean_price,
        'service_details': services_detailed,
        'url': url
    }])


def save_execution_status(result, input_df, index, status):
    result = result[['brand', 'hsn', 'tsn', 'model', 'min_price',
                     'max_price', 'mean_price', 'km', 'main_services',
                     'service_name', 'service_overview', 'service_details', 'url']]
    input_df.loc[index, 'Status'] = status
    input_df.to_csv(csv_input, index=False)
    with open(csv_output, 'a') as f:
        result.to_csv(f, header=False, index=False, encoding='utf-8')
    print([elem for elem in input_df.loc[index]])


if __name__ == '__main__':
    main()
