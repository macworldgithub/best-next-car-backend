# import os
# from dotenv import load_dotenv
# from fastapi import FastAPI, Request, UploadFile, File, HTTPException
# from fastapi.responses import JSONResponse
# from motor.motor_asyncio import AsyncIOMotorClient
# from pydantic import BaseModel
# from fastapi import Query

# from typing import Optional, Dict, Any
# import requests
# import datetime
# from bson import ObjectId
# from fastapi.openapi.utils import get_openapi
# from bs4 import BeautifulSoup
# import re
# import time
# import uuid
# from datetime import datetime, timezone, timedelta
# from dateutil.parser import parse
# import platform
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.chrome.service import Service
# from webdriver_manager.chrome import ChromeDriverManager
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from apscheduler.schedulers.background import BackgroundScheduler
# from math import ceil
# from urllib.parse import urljoin
# import pymongo
# from fastapi.middleware.cors import CORSMiddleware
# load_dotenv()

# # Environment Variables
# XAI_API_KEY = os.getenv("XAI_API_KEY")
# REDBOOK_API_KEY = os.getenv("REDBOOK_API_KEY")  # Kept but not used
# MONGO_URI = os.getenv("MONGO_URI")

# # FastAPI App
# app = FastAPI(title="Best Next Car Backend - Chatbot Focus")
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
# # Custom OpenAPI schema (optional, for customization)
# def custom_openapi():
#     if app.openapi_schema:
#         return app.openapi_schema
#     openapi_schema = get_openapi(
#         title=app.title,
#         version="1.0.0",
#         description="API for the Best Next Car chatbot backend",
#         routes=app.routes,
#     )
#     app.openapi_schema = openapi_schema
#     return app.openapi_schema

# app.openapi = custom_openapi

# # MongoDB Client (async for endpoints)
# client = AsyncIOMotorClient(MONGO_URI)
# db = client.get_default_database()
# conversations = db.conversations  # Collection for conversation states
# leads = db.leads  # Collection for prequalified leads
# uploads = db.uploads  # Collection for document metadata
# lots_collection = db.lots  # Current and upcoming lots
# sold_collection = db.sold  # Sold archive

# # Sync MongoDB Client for scraping
# sync_client = pymongo.MongoClient(MONGO_URI)
# sync_db = sync_client.get_default_database()
# sync_lots_collection = sync_db.lots
# sync_sold_collection = sync_db.sold

# # Create indexes for fast queries
# sync_lots_collection.create_index([('auction_date', 1), ('source', 1), ('make', 1), ('model', 1), ('location', 1), ('scrape_time', 1)])
# sync_sold_collection.create_index([('auction_date', 1), ('source', 1), ('make', 1), ('model', 1), ('location', 1)])

# # Buyers Premiums (approximate percentages, update as needed)
# house_premiums = {
#     'tradinggarage': 0.12,
#     'carbids': 0.15,
#     'collectingcars': 0.06,
#     'bennettsclassicauctions': 0.125,
#     'burnsandco': 0.15,
#     'lloydsonline': 0.20,
#     'seven82motors': 0.10,
#     'chicaneauctions': 0.12,
#     'doningtonauctions': 0.125
# }

# # Scraping Sources
# SOURCES = [
#     {'url': 'https://www.tradinggarage.com', 'name': 'tradinggarage'},
#     {'url': 'https://collectingcars.com/buy?refinementList%5BlistingStage%5D%5B0%5D=live&refinementList%5BregionCode%5D%5B0%5D=APAC&refinementList%5BcountryCode%5D%5B0%5D=AU', 'name': 'collectingcars'},
#     {'url': 'https://www.bennettsclassicauctions.com.au', 'name': 'bennettsclassicauctions'},
#     {'url': 'https://carbids.com.au/t/unique-and-classic-car-auctions#!?page=1&count=96&filter%5BDisplay%5D=true', 'name': 'carbids'},
#     {'url': 'https://www.lloydsonline.com.au/AuctionLots.aspx?stype=0&stypeid=0&cid=410&smode=0', 'name': 'lloydsonline'},
#     {'url': 'https://www.chicaneauctions.com.au', 'name': 'chicaneauctions'},
#     {'url': 'https://www.seven82motors.com.au', 'name': 'seven82motors'},
#     # Add others if needed
# ]

# # Pydantic Models
# class Message(BaseModel):
#     phone: str  # Used as session identifier
#     body: str

# class LVRInput(BaseModel):
#     vehicle_value: float
#     loan_amount: float

# class ConversationState(BaseModel):
#     phone: str
#     language: str = "English"
#     path: Optional[str] = None  # "preowned" or "new"
#     name: Optional[str] = None
#     budget: Optional[Dict[str, float]] = None  # {"min": float, "max": float}
#     finance_needed: bool = False
#     income_bracket: Optional[str] = None
#     employment_status: Optional[str] = None
#     commitments: Optional[str] = None
#     loan_term: Optional[int] = None
#     down_payment: Optional[float] = None
#     vehicle_interest: Optional[str] = None  # For new path
#     specs: Optional[Dict[str, str]] = None  # Fuel type, etc.
#     selected_vehicle: Optional[Dict] = None
#     last_message_time: datetime = datetime.now(timezone.utc)
#     history: list = []  # List of {"role": "user/system", "content": str}

# # LVR Calculation (as per scope)
# def calculate_lvr(vehicle_value: float, loan_amount: float) -> Dict[str, Any]:
#     if vehicle_value <= 0:
#         return {"lvr_percent": 0, "tier": "invalid"}
#     lvr = (loan_amount / vehicle_value) * 100
#     if lvr <= 100:
#         tier = "preferred"
#     elif lvr <= 130:
#         tier = "acceptable"
#     else:
#         tier = "high_risk"
#     return {"lvr_percent": round(lvr, 1), "tier": tier}

# def get_driver():
#     options = Options()
#     options.add_argument('--headless')  # Modern way to set headless mode
#     options.add_argument('--disable-gpu')  # Often needed for headless
#     options.add_argument('--window-size=1920,1080')  # Avoids some rendering issues
#     if platform.system() == 'Linux':
#         options.add_argument('--no-sandbox')  # Critical for Linux servers
#         options.add_argument('--disable-dev-shm-usage')  # Handles small /dev/shm in containers
#         options.add_argument('--remote-debugging-port=9222')  # For stability in some envs
#     service = Service(ChromeDriverManager().install())
#     return webdriver.Chrome(service=service, options=options)

# def parse_price(price_str):
#     if not price_str or price_str == 'TBA':
#         return None
#     try:
#         if isinstance(price_str, (int, float)):
#             val = float(price_str)
#             return {'low': val, 'high': val}
#         price_str = str(price_str).replace(',', '').replace('$', '').strip()
#         m = re.match(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)', price_str)
#         if m:
#             return {'low': float(m.group(1)), 'high': float(m.group(2))}
#         m = re.match(r'(\d+(?:\.\d+)?)', price_str)
#         if m:
#             val = float(m.group(1))
#             return {'low': val, 'high': val}
#     except:
#         pass
#     return None

# def scrape_site(source):
#     url = source['url']
#     name = source['name']
#     if name == 'bennettsclassicauctions':
#         return scrape_bennetts(url)
#     elif name == 'burnsandco':
#         return scrape_burnsandco(url)
#     elif name == 'carbids':
#         return scrape_carbids(url)
#     elif name == 'tradinggarage':
#         return scrape_tradinggarage(url)
#     elif name == 'collectingcars':
#         return scrape_collectingcars()
#     elif name == 'lloydsonline':
#         return scrape_lloydsonline()
#     elif name == 'chicaneauctions':
#         return scrape_chicane()
#     elif name == 'seven82motors':
#         return scrape_seven82motors()
#     else:
#         # Generic scraper for other sites
#         try:
#             driver = get_driver()
#             driver.get(url)
#             soup = BeautifulSoup(driver.page_source, 'html.parser')
#             driver.quit()
#             listings = []
#             item_class = 'auction-item' # Adjust per site as needed
#             for item in soup.find_all('div', class_=item_class):
#                 lot = parse_lot(item, url)
#                 if lot and is_classic(lot):
#                     lot['source'] = name
#                     listings.append(lot)
#             return listings
#         except Exception as e:
#             print(f"Error scraping {url}: {e}")
#             return []

# def scrape_tradinggarage(base_url="https://www.tradinggarage.com"):
#     listings = []
#     session = requests.Session()
#     session.headers.update({
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
#         'Accept': 'application/json',
#         'Referer': 'https://www.tradinggarage.com/',
#     })
#     endpoints = {
#         'live': 'https://portal.tradinggarage.com/api/v1/auctions?status=live',
#         'coming_soon': 'https://portal.tradinggarage.com/api/v1/auctions?status=coming_soon'
#     }
#     for status, api_url in endpoints.items():
#         try:
#             r = session.get(api_url, timeout=12)
#             if r.status_code != 200:
#                 continue
#             data = r.json()
#             auctions = data.get('data', []) or data.get('auctions', []) or []
#             for auction in auctions:
#                 if auction.get('object_type') != 'vehicle':
#                     continue
#                 title = auction.get('title', 'Unknown Car')
#                 year_str = ''
#                 make = ''
#                 model = ''
#                 m = re.search(r'(\d{4})\s*([a-zA-Z0-9\-() ]+)\s+(.+)', title)
#                 if m:
#                     year_str = m.group(1)
#                     make = m.group(2).strip()
#                     model = m.group(3).strip()
#                 try:
#                     year = int(year_str)
#                 except:
#                     year = 0
#                 price_str = auction.get('last_bid', '0')
#                 auction_date = None
#                 try:
#                     auction_date = parse(auction['auction_end_at'])
#                 except:
#                     pass
#                 images = [auction.get('title_image', '')]
#                 url = f"https://www.tradinggarage.com/products/{auction.get('slug', '')}"
#                 reserve = 'No' if auction.get('no_reserve', False) else 'Yes'
#                 location = 'Online / Melbourne'
#                 description = ''
#                 odometer = ''
#                 lot = {
#                     'source': 'tradinggarage',
#                     'status': auction['status']['name'],
#                     'auction_id': auction['id'],
#                     'title': title,
#                     'year': year,
#                     'make': make,
#                     'model': model,
#                     'odometer': odometer,
#                     'price_range': parse_price(price_str),
#                     'auction_date': auction_date,
#                     'location': location,
#                     'images': images,
#                     'url': url,
#                     'description': description,
#                     'reserve': reserve,
#                     'scrape_time': datetime.now(timezone.utc)
#                 }
#                 if is_classic(lot):
#                     listings.append(lot)
#         except Exception as e:
#             pass
#     return listings

# def scrape_collectingcars():
#     listings = []
#     api_url = "https://dora.production.collecting.com/multi_search"
#     headers = {
#         'x-typesense-api-key': 'aKIufK0SfYHMRp9mUBkZPR7pksehPBZq',
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
#         'Accept': 'application/json',
#         'Content-Type': 'application/json',
#         'Referer': 'https://collectingcars.com/',
#     }
#     base_payload = {
#         "searches": [
#             {
#                 "query_by": "title,productMake,vehicleMake,productYear,tags,lotType,driveSide,location,collectionId,modelId",
#                 "query_by_weights": "9,8,7,6,5,4,3,2,1,0",
#                 "text_match_type": "sum_score",
#                 "sort_by": "rank:asc",
#                 "highlight_full_fields": "*",
#                 "facet_by": "lotType, regionCode, countryCode, saleFormat, noReserve, isBoosted, productMake, vendorType, driveSide, listingStage, tags",
#                 "max_facet_values": 999,
#                 "facet_counts": True,
#                 "facet_stats": True,
#                 "facet_distribution": True,
#                 "facet_return_parent": True,
#                 "collection": "production_cars",
#                 "q": "*",
#                 "filter_by": "listingStage:=[`live`] && countryCode:=[`AU`] && regionCode:=[`APAC`]",
#                 "page": 1,
#                 "per_page": 50
#             }
#         ]
#     }
#     page = 1
#     while True:
#         base_payload["searches"][0]["page"] = page
#         try:
#             response = requests.post(api_url, headers=headers, json=base_payload, timeout=15)
#             if response.status_code != 200:
#                 break
#             data = response.json()
#             if "results" not in data or not data["results"]:
#                 break
#             result = data["results"][0]
#             hits = result.get("hits", [])
#             if not hits:
#                 break
#             for hit in hits:
#                 doc = hit.get("document", {})
#                 if doc.get('lotType') != 'car':
#                     continue
#                 title = doc.get('title', 'Unknown Car')
#                 year_str = doc.get('productYear', '')
#                 try:
#                     year = int(year_str)
#                 except:
#                     year = 0
#                 make = doc.get('productMake', '') or doc.get('vehicleMake', '')
#                 model = doc.get('modelName', '') + ' ' + doc.get('variantName', '').strip()
#                 price_str = doc.get('currentBid', 0)
#                 auction_date = None
#                 try:
#                     auction_date = parse(doc['dtStageEndsUTC'])
#                 except:
#                     pass
#                 images = [doc.get('mainImageUrl', '')]
#                 url = f"https://collectingcars.com/for-sale/{doc.get('slug', '')}"
#                 reserve = 'No' if doc.get('noReserve') == "true" else 'Yes'
#                 location = doc.get('location', 'Australia')
#                 description = '' # No description in data
#                 odometer = doc['features'].get('mileage', '')
#                 transmission = doc['features'].get('transmission', extract_transmission(title))
#                 body_style = extract_body_style(title)
#                 fuel_type = doc['features'].get('fuelType', '')
#                 lot = {
#                     'source': 'collectingcars',
#                     'status': doc['listingStage'],
#                     'auction_id': doc['auctionId'],
#                     'title': title,
#                     'year': year,
#                     'make': make,
#                     'model': model,
#                     'odometer': odometer,
#                     'price_range': parse_price(price_str),
#                     'auction_date': auction_date,
#                     'location': location,
#                     'images': images,
#                     'url': url,
#                     'description': description,
#                     'reserve': reserve,
#                     'body_style': body_style,
#                     'transmission': transmission,
#                     'fuel_type': fuel_type,
#                     'scrape_time': datetime.now(timezone.utc)
#                 }
#                 if is_classic(lot):
#                     listings.append(lot)
#             page += 1
#             time.sleep(1.2)
#         except Exception as e:
#             break
#     return listings

# def scrape_chicane(url='https://www.chicaneauctions.com.au/february-2026-classic-car-auction/'):
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
#                       '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
#     }
#     try:
#         resp = requests.get(url, headers=headers, timeout=20)
#         resp.raise_for_status()
#     except Exception as e:
#         print(f"Error fetching Chicane page: {e}")
#         return []
#     soup = BeautifulSoup(resp.text, 'html.parser')
#     listings = []
#     base_url = 'https://www.chicaneauctions.com.au'
#     for item in soup.select('.promo_box'):
#         try:
#             button = item.select_one('.desc_wrapper .button')
#             link = button if button else item.select_one('.desc_wrapper a')
#             if not link:
#                 continue
#             relative_href = link.get('href', '').strip()
#             if not relative_href:
#                 continue
#             full_url = relative_href if relative_href.startswith('http') else base_url + relative_href
#             if '/sell/' in full_url.lower():
#                 continue
#             title_tag = item.select_one('.desc_wrapper .title')
#             title = title_tag.get_text(strip=True) if title_tag else ''
#             if not title:
#                 continue
#             title_upper = title.upper()
#             if '- OPEN POSITION -' in title_upper or 'STAY TUNED' in title_upper:
#                 continue
#             img_tag = item.select_one('.photo_wrapper img')
#             img_src = None
#             if img_tag:
#                 img_src = img_tag.get('data-src') or img_tag.get('src')
#                 if img_src and img_src.startswith('//'):
#                     img_src = 'https:' + img_src
#             if not img_src or 'upcoming-classic-car-auction-house.png' in img_src:
#                 continue
#             images = [img_src] if img_src else []
#             lot_num = None
#             m = re.search(r'(?:lot[-_\s]*)(\d+)', full_url, re.IGNORECASE)
#             if m:
#                 lot_num = m.group(1)
#             if not lot_num:
#                 m = re.search(r'(?:lot|Lot|LOT)\s*(\d+)', title, re.IGNORECASE)
#                 if m:
#                     lot_num = m.group(1)
#             year = None
#             make = ''
#             model = ''
#             m = re.match(r'^(\d{4})\s+([A-Za-z0-9\-]+(?:\s+[A-Za-z0-9\-]+)*?)(?:\s+(.+?))?(?:\s*-|$)', title.strip())
#             if m:
#                 try:
#                     year = int(m.group(1))
#                 except:
#                     pass
#                 make = (m.group(2) or '').strip()
#                 model = (m.group(3) or '').strip()
#             if not year:
#                 ym = re.search(r'\b(19\d{2}|20\d{2})\b', title)
#                 if ym:
#                     year = int(ym.group(1))
#             location = {
#                 'city': 'Melbourne',
#                 'state': 'VIC',
#                 'country': 'Australia'
#             }
#             lot = {
#                 'source': 'chicaneauctions',
#                 'auction_id': lot_num or title.lower().replace(' ', '-').replace('--', '-'),
#                 'title': title,
#                 'url': full_url,
#                 'year': year,
#                 'make': make,
#                 'model': model,
#                 'vehicle': {
#                     'year': year,
#                     'make': make,
#                     'model': model,
#                 },
#                 'price': {
#                     'current': None,  # not shown on pre-catalogue
#                     'reserve': 'Unknown',
#                 },
#                 'auction_end': None,  # not shown yet
#                 'location': location,
#                 'images': images,
#                 'condition': {
#                     'comment': title,  # can be improved later from detail page
#                 },
#                 'status': 'upcoming',
#                 'scrape_time': datetime.now(timezone.utc).isoformat(),
#             }
#             if is_classic(lot):
#                 listings.append(lot)
#         except Exception as e:
#             print(f"Error parsing one Chicane promo_box: {e}")
#             continue
#     return listings

# def scrape_lloydsonline(url='https://www.lloydsonline.com.au/AuctionLots.aspx?stype=0&stypeid=0&cid=410&smode=0'):
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
#     }
#     try:
#         resp = requests.get(url, headers=headers, timeout=20)
#         if resp.status_code != 200:
#             print(f"Lloyds returned {resp.status_code}")
#             return []
#         html_content = resp.text
#     except Exception as e:
#         print(f"Error fetching Lloyds: {e}")
#         return []
#     soup = BeautifulSoup(html_content, 'html.parser')
#     listings = []
#     base_url = 'https://www.lloydsonline.com.au'
#     for item in soup.select('.gallery_item.lot_list_item'):
#         try:
#             link = item.select_one('a[href^="LotDetails.aspx"]')
#             relative_href = link.get('href') if link else None
#             full_url = None
#             if relative_href:
#                 full_url = base_url + '/' + relative_href.lstrip('/')
#             lot_num_elem = item.select_one('.lot_num')
#             lot_num = lot_num_elem.text.strip() if lot_num_elem else None
#             img_tag = item.select_one('.lot_img img')
#             img_src = None
#             if img_tag and img_tag.has_attr('src'):
#                 img_src = img_tag['src'].strip()
#                 if img_src.startswith('//'):
#                     img_src = 'https:' + img_src
#             images = [img_src] if img_src else []
#             desc_elem = item.select_one('.lot_desc')
#             title = desc_elem.get_text(strip=True) if desc_elem else ''
#             year = None
#             make = ''
#             model = ''
#             m = re.match(r'^(\d{4})\s+(.+?)\s+(.+?)(?:\s+|$)', title)
#             if m:
#                 try:
#                     year = int(m.group(1))
#                 except ValueError:
#                     pass
#                 make = m.group(2).strip()
#                 model = m.group(3).strip()
#             bid_tag = item.select_one('.lot_cur_bid span, .lot_bidding span')
#             current_bid_str = bid_tag.get_text(strip=True) if bid_tag else '0'
#             current_bid = None
#             try:
#                 current_bid = float(re.sub(r'[^\d.]', '', current_bid_str))
#             except (ValueError, TypeError):
#                 pass
#             time_rem_tag = item.select_one('[data-seconds_rem]')
#             seconds_rem = 0
#             if time_rem_tag and time_rem_tag.has_attr('data-seconds_rem'):
#                 try:
#                     seconds_rem = int(time_rem_tag['data-seconds_rem'])
#                 except ValueError:
#                     pass
#             auction_end = datetime.now(timezone.utc) + timedelta(seconds=seconds_rem) if seconds_rem > 0 else None
#             location_img = item.select_one('.auctioneer-location img')
#             state_src = location_img.get('src', '').split('/')[-1] if location_img else ''
#             state_map = {
#                 's_1.png': 'ACT', 's_2.png': 'NT', 's_3.png': 'NSW',
#                 's_4.png': 'QLD', 's_5.png': 'SA', 's_6.png': 'TAS',
#                 's_7.png': 'WA', 's_8.png': 'VIC',
#             }
#             state = state_map.get(state_src, '')
#             location = {'state': state}
#             unreserved = item.select_one('.sash.ribbon-blue')
#             reserve = 'No' if unreserved and 'UNRESERVED' in (unreserved.get_text(strip=True) or '').upper() else 'Yes'
#             vehicle = {
#                 'year': year,
#                 'make': make,
#                 'model': model,
#             }
#             price = {
#                 'current': current_bid,
#             }
#             condition = {
#                 'comment': title,
#             }
#             lot = {
#                 'source': 'lloydsonline',
#                 'auction_id': lot_num,  # or use data-lot_id if available
#                 'title': title,
#                 'url': full_url,
#                 'year': year,
#                 'make': make,
#                 'model': model,
#                 'vehicle': vehicle,
#                 'price': price,
#                 'auction_end': auction_end,
#                 'location': location,
#                 'images': images,
#                 'condition': condition,
#                 'reserve': reserve,
#                 'status': 'live' if seconds_rem > 0 else 'ended',
#                 'scrape_time': datetime.now(timezone.utc),
#             }
#             if is_classic(lot):
#                 listings.append(lot)
#         except Exception as e:
#             print(f"Error parsing Lloyds lot: {str(e)}")
#     return listings

# def scrape_carbids_api():
#     listings = []
#     session = requests.Session()
#     session.headers.update({
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
#         'Accept': 'application/json, text/plain, */*',
#         'X-Requested-With': 'XMLHttpRequest',
#         'Referer': 'https://carbids.com.au/',
#         'Origin': 'https://carbids.com.au',
#     })
#     try:
#         home = session.get("https://carbids.com.au/t/unique-and-classic-car-auctions")
#         soup = BeautifulSoup(home.text, 'html.parser')
#         token_input = soup.find('input', {'name': '__RequestVerificationToken'})
#         if token_input and token_input.get('value'):
#             session.headers['__RequestVerificationToken'] = token_input['value']
#     except:
#         pass
#     page = 0
#     while True:
#         payload = {
#             "top": 96,
#             "skip": page * 96,
#             "sort": {"aucClose": "asc"},
#             "tagName": "Unique and Classic Car Auctions",
#             "filter": {"Display": True}
#         }
#         try:
#             resp = session.post(
#                 "https://carbids.com.au/Search/Tags",
#                 json=payload,
#                 timeout=20
#             )
#             if resp.status_code != 200:
#                 print(f"Carbids API returned {resp.status_code}")
#                 break
#             data = resp.json()
#             auctions = data.get("auctions", [])
#             if not auctions:
#                 break
#             for auc in auctions:
#                 title = auc.get("aucTitle", "").strip()
#                 title_text = auc.get("aucTitleText", title).strip()
#                 short_title = auc.get("aucTitleShortText", title).strip()
#                 year = None
#                 make = ""
#                 model = ""
#                 m = re.match(r'^(\d{1,2}/)?(\d{4})\s+(.+?)\s+(.+?)(?:\s+|$)', title_text)
#                 if m:
#                     year_str = m.group(2)
#                     make = m.group(3).strip()
#                     model = m.group(4).strip()
#                     try:
#                         year = int(year_str)
#                     except:
#                         year = None
#                 if not year and auc.get("aucYear"):
#                     try:
#                         year = int(auc["aucYear"])
#                     except:
#                         pass
#                 make = auc.get("aucMake", make).strip()
#                 model = auc.get("aucModel", model).strip()
#                 current_bid = auc.get("aucCurrentBid", 0.0)
#                 starting_bid = auc.get("aucStartingBid", 1.0)
#                 price_info = {
#                     "current": float(current_bid) if current_bid else None,
#                     "starting": float(starting_bid) if starting_bid else None,
#                     "increment": auc.get("aucBidIncrement", 0.0),
#                     "buyers_premium_text": auc.get("aucBPText", ""),
#                     "gst_note": auc.get("isGstApplicableWording", "")
#                 }
#                 end_date_str = auc.get("aucCloseUtc")
#                 auction_end = None
#                 if end_date_str:
#                     try:
#                         auction_end = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
#                     except:
#                         try:
#                             auction_end = parse(end_date_str)
#                         except:
#                             pass
#                 location = {
#                     "city": auc.get("aucCity", ""),
#                     "state": auc.get("aucState", ""),
#                     "address": auc.get("aucAddressLocation", ""),
#                     "pickup": auc.get("aucPickupAvailable", False),
#                     "freight": auc.get("aucFreightAvailable", False),
#                     "freight_limits": auc.get("aucItemFreightLimits", "")
#                 }
#                 vehicle = {
#                     "year": year,
#                     "make": make,
#                     "model": model,
#                     "odometer_km": auc.get("aucOdometerNumber"),
#                     "odometer_display": auc.get("aucOdometer", ""),
#                     "transmission": auc.get("aucTransmission"),
#                     "fuel_type": auc.get("aucFuelType"),
#                     "engine_capacity": auc.get("aucCapacity"),
#                     "cylinders": auc.get("aucCylinder"),
#                     "drivetrain": auc.get("aucDrv"),
#                 }
#                 images = []
#                 base = auc.get("aucCarsThumbnailUrl", auc.get("aucThumbnailUrl", ""))
#                 if base:
#                     images.append(base)
#                 for size in ["small", "medium", "large"]:
#                     key = f"aucCars{size.capitalize()}ThumbnailUrl"
#                     if auc.get(key):
#                         images.append(auc[key])
#                 medium_list = auc.get("aucMediumThumbnailUrlList", [])
#                 images.extend([url for url in medium_list if url])
#                 condition = {
#                     "body": auc.get("aucBodyCondition"),
#                     "paint": auc.get("aucPaintCondition"),
#                     "features_text": auc.get("aucFeaturesText"),
#                     "key_facts": auc.get("aucKeyFactsText"),
#                     "comment": auc.get("aucComment"),
#                     "service_history": auc.get("aucServiceHistory"),
#                 }
#                 lot = {
#                     "source": "carbids",
#                     "auction_id": auc.get("aucID"),
#                     "reference_number": auc.get("aucReferenceNo"),
#                     "title": title_text,
#                     "short_title": short_title,
#                     "url": "https://carbids.com.au/" + auc.get("AucDetailsUrlLink", "").lstrip("/"),
#                     "year": year,
#                     "make": make,
#                     "model": model,
#                     "vehicle": vehicle,
#                     "price": price_info,
#                     "auction_end": auction_end,
#                     "location": location,
#                     "images": images[:8], # limit to 8 for storage
#                     "condition": condition,
#                     "reserve": "Yes", # currently no reserve field → assume Yes
#                     "status": "live", # we only get live auctions here
#                     "scrape_time": datetime.now(timezone.utc),
#                 }
#                 if is_classic(lot):
#                     listings.append(lot)
#             page += 1
#             time.sleep(1.3) # polite delay
#         except Exception as e:
#             print("Error in carbids API loop:", str(e))
#             break
#     return listings

# def scrape_carbids(base_url):
#     listings_api = scrape_carbids_api()
#     combined = listings_api
#     seen_urls = set()
#     unique = []
#     for lot in combined:
#         u = lot.get("url")
#         if u and u not in seen_urls:
#             seen_urls.add(u)
#             unique.append(lot)
#     return unique

# def scrape_bennetts(base_url="https://www.bennettsclassicauctions.com.au"):
#     pages = [base_url, base_url + '/off-site.php']
#     all_listings = []
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
#     }
#     for page_url in pages:
#         try:
#             resp = requests.get(page_url, headers=headers, timeout=20)
#             resp.raise_for_status()
#             soup = BeautifulSoup(resp.text, 'html.parser')
#             sitename = soup.find('div', id='sitename')
#             h3 = sitename.find('h3') if sitename else None
#             auction_text = h3.text.strip() if h3 else ''
#             date_match = re.search(r'(\d{1,2}[ST|ND|RD|TH]{0,2} \w+ \d{4})', auction_text.upper())
#             time_match = re.search(r'@ (\d{1,2}[AP]M)', auction_text.upper())
#             auction_date_str = ''
#             if date_match:
#                 date_str = re.sub(r'([ST|ND|RD|TH])', '', date_match.group(1))
#                 auction_date_str += date_str
#             if time_match:
#                 auction_date_str += ' ' + time_match.group(1)
#             auction_date = None
#             try:
#                 auction_date = parse(auction_date_str)
#             except:
#                 pass
#             sections = soup.find_all('div', class_='clear')
#             for section in sections:
#                 column = section.find('div', class_='column column-600 column-left')
#                 if column:
#                     h3_cat = column.find('h3')
#                     category = h3_cat.text.strip() if h3_cat else ''
#                     table = column.find('table')
#                     if table:
#                         tbody = table.find('tbody')
#                         trs = tbody.find_all('tr') if tbody else table.find_all('tr')
#                         for tr in trs[1:]:  # Skip header
#                             tds = tr.find_all('td')
#                             if len(tds) >= 7:  # Ensure enough columns
#                                 photo_td = tds[0]
#                                 a = photo_td.find('a')
#                                 detail_url = base_url + '/' + a['href'].lstrip('/') if a else ''
#                                 img = photo_td.find('img')
#                                 image_src = base_url + '/' + img['src'].lstrip('/') if img and img['src'].startswith('images') else (img['src'] if img else '')
#                                 make = tds[1].text.strip()
#                                 stock_model = tds[2].text.strip()
#                                 parts = stock_model.split('/')
#                                 stock_ref = parts[0].strip() if parts else ''
#                                 model = parts[1].strip() if len(parts) > 1 else stock_model
#                                 year_str = tds[3].text.strip()
#                                 try:
#                                     year = int(year_str)
#                                 except:
#                                     year = 0
#                                 options = tds[4].text.strip()
#                                 location_td = tds[5]
#                                 location = location_td.text.strip().replace('\n', '').replace('br /', '')
#                                 lot = {
#                                     'source': 'bennettsclassicauctions',
#                                     'make': make,
#                                     'model': model,
#                                     'year': year,
#                                     'price_range': None,
#                                     'auction_date': auction_date,
#                                     'location': location,
#                                     'images': [image_src] if image_src else [],
#                                     'url': detail_url,
#                                     'description': options,
#                                     'reserve': 'Yes',
#                                     'body_style': extract_body_style(options),
#                                     'transmission': extract_transmission(options),
#                                     'scrape_time': datetime.now(timezone.utc)
#                                 }
#                                 if is_classic(lot):
#                                     all_listings.append(lot)
#         except Exception as e:
#             print(f"Error scraping Bennetts ({page_url}): {str(e)}")
#     return all_listings

# def scrape_burnsandco(base_url="https://burnsandcoauctions.com.au"):
#     pages = [base_url + '/current-auctions/', base_url + '/upcoming-auctions/']
#     all_listings = []
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
#     }
#     for page_url in pages:
#         try:
#             resp = requests.get(page_url, headers=headers, timeout=20)
#             resp.raise_for_status()
#             soup = BeautifulSoup(resp.text, 'html.parser')
#             articles = soup.find_all('article', class_='regular masonry-blog-item')
#             for article in articles:
#                 img_link = article.find('a', class_='img-link')
#                 detail_url = img_link['href'] if img_link else ''
#                 img = img_link.find('img') if img_link else None
#                 image_src = img['src'] if img else ''
#                 meta_category = article.find('span', class_='meta-category')
#                 category = meta_category.text.strip() if meta_category else ''
#                 date_item = article.find('span', class_='date-item')
#                 auction_date_str = date_item.text.strip() if date_item else ''
#                 auction_date = None
#                 try:
#                     auction_date = parse(auction_date_str)
#                 except:
#                     pass
#                 title_a = article.find('h3', class_='title').find('a') if article.find('h3', class_='title') else None
#                 title = title_a.text.strip() if title_a else ''
#                 excerpt = article.find('div', class_='excerpt').text.strip() if article.find('div', class_='excerpt') else ''
#                 place = article.find('p', class_='place').text.strip() if article.find('p', class_='place') else ''
#                 bid_links = article.find_all('p', class_='registration_bidding_link')
#                 for bid_p in bid_links:
#                     bid_a = bid_p.find('a')
#                     bid_url = bid_a['href'] if bid_a else ''
#                     catalogue_lots = scrape_catalogue(bid_url)
#                     for cat_lot in catalogue_lots:
#                         cat_lot['auction_date'] = auction_date or cat_lot.get('auction_date')
#                         cat_lot['location'] = place or cat_lot.get('location')
#                         cat_lot['source'] = 'burnsandco'
#                         all_listings.append(cat_lot)
#         except Exception as e:
#             print(f"Error scraping Burns and Co ({page_url}): {str(e)}")
#     return all_listings

# def scrape_seven82motors():
#     listings = []
#     auction_slug = "march-29th-2026"
#     api_url = f"https://seven82-json-sb.manage.auction/listings/auctions/{auction_slug}?amt=100"
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
#                       '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
#         'Accept': 'application/json',
#         'Referer': 'https://www.seven82motors.com.au/',
#     }
#     try:
#         resp = requests.get(api_url, headers=headers, timeout=20)
#         resp.raise_for_status()
#         data = resp.json()
#         auction_title = data.get("heading", "Unknown Auction Date")
#         auction_date = None
#         date_str_candidates = [
#             auction_title,
#             data.get("breadcrumbs", [{}])[0].get("title", ""),
#             f"{auction_title} 2026",
#             auction_slug.replace("-", " ").title()
#         ]
#         for candidate in date_str_candidates:
#             if not candidate:
#                 continue
#             try:
#                 auction_date = parse(candidate, fuzzy=True, dayfirst=False)
#                 if auction_date.year >= 2025:
#                     break
#             except:
#                 continue
#         if not auction_date:
#             auction_date = datetime.now(timezone.utc) + timedelta(days=60)
#         items = data.get("items", [])
#         for item in items:
#             if item.get("dummy_lot", 0) == 1:
#                 continue
#             title = (item.get("title") or "").strip()
#             if not title:
#                 continue
#             if any(phrase in title.upper() for phrase in [
#                 "SELL YOUR CAR", "CONSIGN", "REGISTER AND BID", "LEARN HOW TO"
#             ]):
#                 continue
#             year = None
#             make = ""
#             model = ""
#             clean_title = re.sub(
#                 r'^(NO RESERVE!?\s*|RARE\s*|FULLY RESTORED\s*|CUSTOM\s*)',
#                 '', title, flags=re.IGNORECASE
#             ).strip()
#             m = re.match(r'^(\d{4})\s+(.+?)(?:\s+(.+?))?(?:\s+|$)', clean_title)
#             if m:
#                 try:
#                     year = int(m.group(1))
#                 except:
#                     pass
#                 make_model_part = (m.group(2) or "").strip()
#                 extra = (m.group(3) or "").strip()
#                 parts = make_model_part.split(maxsplit=1)
#                 if parts:
#                     make = parts[0].strip()
#                     if len(parts) > 1:
#                         model = parts[1].strip()
#                     model = f"{model} {extra}".strip()
#             reserve = "No" if "NO RESERVE" in title.upper() else "Yes"
#             images = []
#             featured = item.get("media_featured", [])
#             if isinstance(featured, list):
#                 for img_obj in featured:
#                     if isinstance(img_obj, dict):
#                         src = img_obj.get("src")
#                         if src and "catalog/" in src:
#                             clean_src = src.lstrip('/')
#                             full_url = f"https://seven82motors.mymedia.delivery/{clean_src}"
#                             if full_url not in images:
#                                 images.append(full_url)
#             main_img = item.get("image")
#             if main_img and "catalog/" in main_img:
#                 clean_main = main_img.lstrip('/')
#                 full_main = f"https://seven82motors.mymedia.delivery/{clean_main}"
#                 if full_main not in images:
#                     images.insert(0, full_main)
#             seen = set()
#             clean_images = []
#             for url in images:
#                 if url and url not in seen:
#                     seen.add(url)
#                     if not any(x in url.lower() for x in ["thumb", "small", "placeholder", "watermark"]):
#                         clean_images.append(url)
#             images = clean_images[:12]
#             is_coming_soon = False
#             coming_soon_data = item.get("coming_soon", [])
#             if isinstance(coming_soon_data, list):
#                 for entry in coming_soon_data:
#                     if isinstance(entry, dict):
#                         if entry.get("settings", {}).get("coming_soon") in (True, "1", 1, "true"):
#                             is_coming_soon = True
#                             break
#             lot_path = item.get('path', '').lstrip('/')
#             lot_url = f"https://www.seven82motors.com.au/lot/{lot_path}" if lot_path else ""
#             lot = {
#                 'source': 'seven82motors',
#                 'status': 'upcoming',
#                 'auction_id': item.get("id"),
#                 'lot_number': item.get("number"),
#                 'title': title,
#                 'year': year,
#                 'make': make,
#                 'model': model,
#                 'odometer': None,  # detail page only
#                 'price_range': None,  # not in list view
#                 'auction_date': auction_date,
#                 'location': "Brisbane, QLD (Online)",
#                 'images': images,
#                 'url': lot_url,
#                 'description': (item.get("description_short") or "").strip(),
#                 'reserve': reserve,
#                 'body_style': None,
#                 'transmission': None,
#                 'fuel_type': None,
#                 'scrape_time': datetime.now(timezone.utc),
#                 'coming_soon': is_coming_soon,
#                 'buyers_premium_pct': 8.8,
#                 'auction_title': auction_title,
#                 'raw_filters': item.get("filters", {}),
#             }
#             if is_classic(lot):
#                 listings.append(lot)
#     except Exception as e:
#         print(f"[seven82motors] Error scraping {auction_slug}: {e}")
#     return listings

# def scrape_catalogue(catalogue_url):
#     listings = []
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
#     }
#     try:
#         resp = requests.get(catalogue_url, headers=headers, timeout=20)
#         resp.raise_for_status()
#         soup = BeautifulSoup(resp.text, 'html.parser')
#         table = soup.find('table')  # Or find('table', class_='catalogue-table') if specific class
#         if table:
#             trs = table.find_all('tr')
#             for tr in trs[1:]:  # Skip header row
#                 tds = tr.find_all('td')
#                 if len(tds) < 4:
#                     continue
#                 lot_number = tds[0].text.strip()
#                 desc_td = tds[1]
#                 desc = desc_td.text.strip()
#                 match = re.match(r'(\d{4})? ?(.*?) (.*)', desc)
#                 year_str = match.group(1) if match and match.group(1) else ''
#                 try:
#                     year = int(year_str)
#                 except:
#                     year = 0
#                 make = match.group(2) if match else ''
#                 model = match.group(3) if match else desc
#                 images = [urljoin(catalogue_url, img['src']) for img in tr.find_all('img') if 'src' in img.attrs]
#                 detail_a = desc_td.find('a')
#                 detail_url = urljoin(catalogue_url, detail_a['href']) if detail_a else ''
#                 current_bid = tds[2].text.strip()
#                 lot = {
#                     'lot_number': lot_number,
#                     'make': make,
#                     'model': model,
#                     'year': year,
#                     'price_range': parse_price(current_bid),
#                     'auction_date': None,
#                     'location': None,
#                     'images': images,
#                     'url': detail_url,
#                     'description': desc,
#                     'reserve': 'Yes',
#                     'body_style': extract_body_style(desc),
#                     'transmission': extract_transmission(desc),
#                     'scrape_time': datetime.now(timezone.utc)
#                 }
#                 if is_classic(lot):
#                     listings.append(lot)
#     except Exception as e:
#         print(f"Error scraping catalogue ({catalogue_url}): {str(e)}")
#     return listings

# def parse_lot(item, url):
#     try:
#         description = item.find('p', class_='desc') or item.find('div', class_='description')
#         description_text = description.text.strip() if description else ''
#         year_elem = item.find('span', class_='year') or item.find('h3')
#         year_str = year_elem.text.strip() if year_elem else '0'
#         try:
#             year = int(year_str)
#         except:
#             year = 0
#         make_elem = item.find('span', class_='make') or item.find('h2')
#         model_elem = item.find('span', class_='model')
#         price_elem = item.find('span', class_='estimate') or item.find('div', class_='price')
#         price_str = price_elem.text.strip() if price_elem else None
#         date_elem = item.find('span', class_='date')
#         location_elem = item.find('span', class_='location')
#         link_elem = item.find('a', class_='lot-link') or item.find('a')
#         lot = {
#             'make': make_elem.text.strip() if make_elem else None,
#             'model': model_elem.text.strip() if model_elem else None,
#             'year': year,
#             'price_range': parse_price(price_str),
#             'auction_date': parse_date(date_elem.text.strip()) if date_elem else None,
#             'location': location_elem.text.strip() if location_elem else 'Online',
#             'images': [img['src'] for img in item.find_all('img', class_='thumbnail')][:6],
#             'url': link_elem['href'] if link_elem else url,
#             'description': description_text,
#             'reserve': 'No' if 'no reserve' in description_text.lower() else 'Yes',
#             'body_style': extract_body_style(description_text),
#             'transmission': extract_transmission(description_text),
#             'scrape_time': datetime.now(timezone.utc)
#         }
#         return lot
#     except:
#         return None

# def parse_date(date_str):
#     try:
#         return parse(date_str)
#     except:
#         return None

# def extract_body_style(desc):
#     lower_desc = desc.lower()
#     styles = ['coupe', 'convertible', 'sedan', 'wagon', 'ute', 'truck']
#     for style in styles:
#         if style in lower_desc:
#             return style.capitalize()
#     return None

# def extract_transmission(desc):
#     lower_desc = desc.lower()
#     if 'manual' in lower_desc:
#         return 'Manual'
#     if 'auto' in lower_desc or 'automatic' in lower_desc:
#         return 'Automatic'
#     return None

# def is_classic(lot):
#     year = lot.get('year')
#     if year is None or not isinstance(year, (int, float)):
#         text = (lot.get('title', '') + ' ' + lot.get('description', '')).lower()
#         has_classic_hint = any(word in text for word in [
#             'classic', 'muscle', 'vintage', 'hot rod', 'restored', 'collector',
#             'holden', 'falcon gt', 'monaro', 'charger', 'mustang', 'corvette'
#         ])
#         return has_classic_hint
#     if year < 2005:
#         return True
#     text = (lot.get('title', '') + ' ' + lot.get('description', '')).lower()
#     modern_classic_keywords = [
#         'hellcat', 'demon', 'supercharged', 'stroker', 'r8', 'gts-r', 'boss 302',
#         'shelby', 'a9x', 'fpv', 'gtr', 'torana', 'monaro'
#     ]
#     return any(kw in text for kw in modern_classic_keywords)

# def normalize_auction_date(ad):
#     if not ad:
#         return None
#     if isinstance(ad, datetime):
#         return ad
#     if isinstance(ad, str):
#         try:
#             return parse(ad)
#         except:
#             return None
#     try:
#         return parse(str(ad))
#     except:
#         return None

# # Scrape all and store in DB (sync version)
# def scrape_all():
#     all_lots = []
#     scrape_start = datetime.now(timezone.utc)
#     for source in SOURCES:
#         lots = scrape_site(source)
#         all_lots.extend(lots)
    
#     for lot in all_lots:
#         lot['scrape_time'] = datetime.now(timezone.utc)
#         lot['auction_date'] = normalize_auction_date(lot.get('auction_date'))
#         if not lot.get('url'):
#             lot['url'] = f"{lot.get('source','unknown')}/{uuid.uuid4()}"
#         sync_lots_collection.update_one(
#             {'url': lot['url']},
#             {'$set': lot, '$setOnInsert': {'first_scraped': scrape_start}},
#             upsert=True
#         )
    
#     now = datetime.now(timezone.utc)
#     ended = list(sync_lots_collection.find({'auction_date': {'$lt': now}}))
#     for end in ended:
#         house = end['source']
#         prem = house_premiums.get(house, 0.15)
#         hammer = end.get('price_range', {}).get('high', 0)
#         total = hammer * (1 + prem)
#         sold_doc = dict(end)
#         sold_doc['hammer_price'] = hammer
#         sold_doc['buyers_premium'] = prem * 100
#         sold_doc['total_price'] = total
#         sync_sold_collection.insert_one(sold_doc)
#         sync_lots_collection.delete_one({'_id': end['_id']})
    
#     two_years_ago = now - timedelta(days=730)
#     sync_sold_collection.delete_many({'auction_date': {'$lt': two_years_ago}})

# # Scheduler for scraping
# scheduler = BackgroundScheduler()
# scheduler.add_job(scrape_all, 'interval', hours=1)
# scheduler.start()

# # Vehicle Fetching using DB (scraped data)
# # async def fetch_vehicles(path: str, criteria: Dict) -> list:
# #     if path != "preowned":
# #         return []  # For "new", no data from sources
    
# #     query = {}
# #     if "min_price" in criteria:
# #         query["price_range.low"] = {"$gte": criteria["min_price"]}
# #     if "max_price" in criteria:
# #         query["price_range.high"] = {"$lte": criteria["max_price"]}
# #     if "interest" in criteria:
# #         interest = criteria["interest"]
# #         query["$or"] = [
# #             {"make": {"$regex": interest, "$options": "i"}},
# #             {"model": {"$regex": interest, "$options": "i"}},
# #             {"title": {"$regex": interest, "$options": "i"}},
# #             {"description": {"$regex": interest, "$options": "i"}}
# #         ]
    
# #     vehicles = await lots_collection.find(query).limit(8).to_list(8)
# #     return [dict(v, _id=str(v["_id"])) for v in vehicles]


# async def fetch_vehicles(path: str, criteria: Dict, page: int, page_size: int):
#     if path != "preowned":
#         return [], 0

#     query = {}

#     if "min_price" in criteria:
#         query["price_range.low"] = {"$gte": criteria["min_price"]}

#     if "max_price" in criteria:
#         query["price_range.high"] = {"$lte": criteria["max_price"]}

#     if "interest" in criteria:
#         interest = criteria["interest"]
#         query["$or"] = [
#             {"make": {"$regex": interest, "$options": "i"}},
#             {"model": {"$regex": interest, "$options": "i"}},
#             {"title": {"$regex": interest, "$options": "i"}},
#             {"description": {"$regex": interest, "$options": "i"}}
#         ]

#     # Pagination logic
#     skip = (page - 1) * page_size

#     total = await lots_collection.count_documents(query)

#     cursor = (
#         lots_collection
#         .find(query)
#         .skip(skip)
#         .limit(page_size)
#     )

#     vehicles = await cursor.to_list(length=page_size)

#     return [dict(v, _id=str(v["_id"])) for v in vehicles], total
# # xAI API Integration for Conversational AI
# async def generate_ai_response(state: ConversationState, user_message: str) -> str:
#     system_prompt = f"""
#     You are an AI car finder for Australian users. Follow the project scope strictly.
#     Handle onboarding, language selection, preowned/new paths, financing with LVR, resumability, personalization, empathy.
#     Be inclusive, compliant with ACL, NCCP, APP. Provide indicative guidance only.
#     Support languages: English, Mandarin, Arabic, Hindi, etc. Respond in selected language.
#     Use name if available. Adapt tone.
#     For finance: Use LVR calculation - call internal API if needed (but simulate here).
#     Present 4-8 vehicle matches from inventory.
#     Allow exploration, comparison, refinement.
#     On selection: Verify, collect docs (prompt for upload), handoff to broker.
#     Additional: Trade-in, insurance, tips.
#     Escalate to human if complex.
#     Allow language switching.
#     State: {state.dict()}
#     If resuming: Welcome back and reference last discussion.
#     """
#     messages = [
#         {"role": "system", "content": system_prompt},
#         *state.history,
#         {"role": "user", "content": user_message}
#     ]
#     url = "https://api.x.ai/v1/chat/completions"
#     headers = {
#         "Authorization": f"Bearer {XAI_API_KEY}",
#         "Content-Type": "application/json"
#     }
#     data = {
#         "model": "grok-3",
#         "messages": messages,
#         "temperature": 0.7,
#         "max_tokens": 500
#     }
#     response = requests.post(url, headers=headers, json=data)
#     if response.status_code == 200:
#         ai_reply = response.json()["choices"][0]["message"]["content"]
#         state.history.append({"role": "user", "content": user_message})
#         state.history.append({"role": "assistant", "content": ai_reply})
#         return ai_reply
#     raise HTTPException(status_code=500, detail="AI response failed")

# # Web Chat Endpoint (for chatbot widget)
# @app.post("/chat")
# async def web_chat(message: Message):
#     state_doc = await conversations.find_one({"phone": message.phone})
#     if state_doc:
#         state = ConversationState(**state_doc)
#         if (datetime.now(timezone.utc) - state.last_message_time).total_seconds() > 3600:
#             welcome_back = f"Welcome back, {state.name or 'there'}! Last time we were looking at {state.path or 'car options'}."
#             message.body = welcome_back + " " + message.body
#     else:
#         state = ConversationState(phone=message.phone)
    
#     try:
#         reply = await generate_ai_response(state, message.body)
#     except Exception as e:
#         reply = "Sorry, something went wrong. Please try again."

#     state.last_message_time = datetime.now(timezone.utc)
#     await conversations.replace_one({"phone": message.phone}, state.dict(), upsert=True)

#     if "handoff" in reply.lower() or "broker" in reply.lower():
#         lead = {
#             "phone": message.phone,
#             "state": state.dict(),
#             "timestamp": datetime.now(timezone.utc)
#         }
#         await leads.insert_one(lead)
#         print("Handoff to broker:", lead)
#         reply += " Connecting you to a broker soon."

#     return {"reply": reply}

# @app.post("/lvr", response_model=Dict)
# def get_lvr(input: LVRInput):
#     return calculate_lvr(input.vehicle_value, input.loan_amount)

# # @app.get("/vehicles")
# # async def get_vehicles(path: str, budget_min: Optional[float] = None, budget_max: Optional[float] = None, interest: Optional[str] = None):
# #     criteria = {}
# #     if budget_min:
# #         criteria["min_price"] = budget_min
# #     if budget_max:
# #         criteria["max_price"] = budget_max
# #     if interest:
# #         criteria["interest"] = interest
# #     vehicles = await fetch_vehicles(path, criteria)
# #     return {"vehicles": vehicles}
# @app.get("/vehicles")
# async def get_vehicles(
#     path: str,
#     budget_min: Optional[float] = None,
#     budget_max: Optional[float] = None,
#     interest: Optional[str] = None,
#     page: int = Query(1, ge=1),
#     page_size: int = Query(8, ge=1, le=50)
# ):
#     criteria = {}

#     if budget_min is not None:
#         criteria["min_price"] = budget_min
#     if budget_max is not None:
#         criteria["max_price"] = budget_max
#     if interest:
#         criteria["interest"] = interest

#     vehicles, total = await fetch_vehicles(path, criteria, page, page_size)

#     return {
#         "page": page,
#         "page_size": page_size,
#         "total_results": total,
#         "total_pages": (total + page_size - 1) // page_size,
#         "vehicles": vehicles
#     }
# @app.post("/upload/{phone}")
# async def upload_document(phone: str, file: UploadFile = File(...)):
#     if not await conversations.find_one({"phone": phone}):
#         raise HTTPException(403, "No active session")
    
#     os.makedirs(f"uploads/{phone}", exist_ok=True)
#     file_path = f"uploads/{phone}/{file.filename}"
#     with open(file_path, "wb") as f:
#         f.write(await file.read())
    
#     meta = {
#         "phone": phone,
#         "file_name": file.filename,
#         "path": file_path,
#         "timestamp": datetime.now(timezone.utc)
#     }
#     await uploads.insert_one(meta)
#     return {"status": "uploaded", "file": file.filename}

# @app.get("/leads")
# async def get_leads():
#     lead_list = []
#     async for lead in leads.find():
#         lead["_id"] = str(lead["_id"])
#         lead_list.append(lead)
#     return {"leads": lead_list}

# @app.get("/")
# def health():
#     return {"status": "healthy"}

# @app.post("/scrape")
# def scrape_endpoint():
#     scrape_all()
#     return {"message": "Scraping completed"}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)
# import os
# from dotenv import load_dotenv
# from fastapi import FastAPI, Request, UploadFile, File, HTTPException
# from fastapi.responses import JSONResponse
# from motor.motor_asyncio import AsyncIOMotorClient
# from pydantic import BaseModel
# from fastapi import Query

# from typing import Optional, Dict, Any
# import requests
# import datetime
# from bson import ObjectId
# from fastapi.openapi.utils import get_openapi
# from bs4 import BeautifulSoup
# import re
# import time
# import uuid
# from datetime import datetime, timezone, timedelta
# from dateutil.parser import parse
# import platform
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.chrome.service import Service
# from webdriver_manager.chrome import ChromeDriverManager
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from apscheduler.schedulers.background import BackgroundScheduler
# from math import ceil
# from urllib.parse import urljoin
# import pymongo
# from fastapi.middleware.cors import CORSMiddleware
# load_dotenv()

# # Environment Variables
# XAI_API_KEY = os.getenv("XAI_API_KEY")
# REDBOOK_API_KEY = os.getenv("REDBOOK_API_KEY")  # Kept but not used
# MONGO_URI = os.getenv("MONGO_URI")

# # FastAPI App
# app = FastAPI(title="Best Next Car Backend - Chatbot Focus")
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
# # Custom OpenAPI schema (optional, for customization)
# def custom_openapi():
#     if app.openapi_schema:
#         return app.openapi_schema
#     openapi_schema = get_openapi(
#         title=app.title,
#         version="1.0.0",
#         description="API for the Best Next Car chatbot backend",
#         routes=app.routes,
#     )
#     app.openapi_schema = openapi_schema
#     return app.openapi_schema

# app.openapi = custom_openapi

# # MongoDB Client (async for endpoints)
# client = AsyncIOMotorClient(MONGO_URI)
# db = client.get_default_database()
# conversations = db.conversations  # Collection for conversation states
# leads = db.leads  # Collection for prequalified leads
# uploads = db.uploads  # Collection for document metadata
# lots_collection = db.lots  # Current and upcoming lots
# sold_collection = db.sold  # Sold archive

# # Sync MongoDB Client for scraping
# sync_client = pymongo.MongoClient(MONGO_URI)
# sync_db = sync_client.get_default_database()
# sync_lots_collection = sync_db.lots
# sync_sold_collection = sync_db.sold

# # Create indexes for fast queries
# sync_lots_collection.create_index([('auction_date', 1), ('source', 1), ('make', 1), ('model', 1), ('location', 1), ('scrape_time', 1)])
# sync_sold_collection.create_index([('auction_date', 1), ('source', 1), ('make', 1), ('model', 1), ('location', 1)])

# # Buyers Premiums (approximate percentages, update as needed)
# house_premiums = {
#     'tradinggarage': 0.12,
#     'carbids': 0.15,
#     'collectingcars': 0.06,
#     'bennettsclassicauctions': 0.125,
#     'burnsandco': 0.15,
#     'lloydsonline': 0.20,
#     'seven82motors': 0.10,
#     'chicaneauctions': 0.12,
#     'doningtonauctions': 0.125
# }

# # Scraping Sources
# SOURCES = [
#     {'url': 'https://www.tradinggarage.com', 'name': 'tradinggarage'},
#     {'url': 'https://collectingcars.com/buy?refinementList%5BlistingStage%5D%5B0%5D=live&refinementList%5BregionCode%5D%5B0%5D=APAC&refinementList%5BcountryCode%5D%5B0%5D=AU', 'name': 'collectingcars'},
#     {'url': 'https://www.bennettsclassicauctions.com.au', 'name': 'bennettsclassicauctions'},
#     {'url': 'https://carbids.com.au/t/unique-and-classic-car-auctions#!?page=1&count=96&filter%5BDisplay%5D=true', 'name': 'carbids'},
#     {'url': 'https://www.lloydsonline.com.au/AuctionLots.aspx?stype=0&stypeid=0&cid=410&smode=0', 'name': 'lloydsonline'},
#     {'url': 'https://www.chicaneauctions.com.au', 'name': 'chicaneauctions'},
#     {'url': 'https://www.seven82motors.com.au', 'name': 'seven82motors'},
#     # Add others if needed
# ]

# # Pydantic Models
# class Message(BaseModel):
#     phone: str  # Used as session identifier
#     body: str

# class LVRInput(BaseModel):
#     vehicle_value: float
#     loan_amount: float

# class ConversationState(BaseModel):
#     phone: str
#     language: str = "English"
#     path: Optional[str] = None  # "preowned" or "new"
#     name: Optional[str] = None
#     budget: Optional[Dict[str, float]] = None  # {"min": float, "max": float}
#     finance_needed: bool = False
#     income_bracket: Optional[str] = None
#     employment_status: Optional[str] = None
#     commitments: Optional[str] = None
#     loan_term: Optional[int] = None
#     down_payment: Optional[float] = None
#     vehicle_interest: Optional[str] = None  # For new path
#     specs: Optional[Dict[str, str]] = None  # Fuel type, etc.
#     selected_vehicle: Optional[Dict] = None
#     last_message_time: datetime = datetime.now(timezone.utc)
#     history: list = []  # List of {"role": "user/system", "content": str}

# # LVR Calculation (as per scope)
# def calculate_lvr(vehicle_value: float, loan_amount: float) -> Dict[str, Any]:
#     if vehicle_value <= 0:
#         return {"lvr_percent": 0, "tier": "invalid"}
#     lvr = (loan_amount / vehicle_value) * 100
#     if lvr <= 100:
#         tier = "preferred"
#     elif lvr <= 130:
#         tier = "acceptable"
#     else:
#         tier = "high_risk"
#     return {"lvr_percent": round(lvr, 1), "tier": tier}

# def get_driver():
#     options = Options()
#     options.add_argument('--headless')  # Modern way to set headless mode
#     options.add_argument('--disable-gpu')  # Often needed for headless
#     options.add_argument('--window-size=1920,1080')  # Avoids some rendering issues
#     if platform.system() == 'Linux':
#         options.add_argument('--no-sandbox')  # Critical for Linux servers
#         options.add_argument('--disable-dev-shm-usage')  # Handles small /dev/shm in containers
#         options.add_argument('--remote-debugging-port=9222')  # For stability in some envs
#     service = Service(ChromeDriverManager().install())
#     return webdriver.Chrome(service=service, options=options)

# def parse_price(price_str):
#     if not price_str or price_str == 'TBA':
#         return None
#     try:
#         if isinstance(price_str, (int, float)):
#             val = float(price_str)
#             return {'low': val, 'high': val}
#         price_str = str(price_str).replace(',', '').replace('$', '').strip()
#         m = re.match(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)', price_str)
#         if m:
#             return {'low': float(m.group(1)), 'high': float(m.group(2))}
#         m = re.match(r'(\d+(?:\.\d+)?)', price_str)
#         if m:
#             val = float(m.group(1))
#             return {'low': val, 'high': val}
#     except:
#         pass
#     return None

# def scrape_site(source):
#     url = source['url']
#     name = source['name']
#     if name == 'bennettsclassicauctions':
#         return scrape_bennetts(url)
#     elif name == 'burnsandco':
#         return scrape_burnsandco(url)
#     elif name == 'carbids':
#         return scrape_carbids(url)
#     elif name == 'tradinggarage':
#         return scrape_tradinggarage(url)
#     elif name == 'collectingcars':
#         return scrape_collectingcars()
#     elif name == 'lloydsonline':
#         return scrape_lloydsonline()
#     elif name == 'chicaneauctions':
#         return scrape_chicane()
#     elif name == 'seven82motors':
#         return scrape_seven82motors()
#     else:
#         # Generic scraper for other sites
#         try:
#             driver = get_driver()
#             driver.get(url)
#             soup = BeautifulSoup(driver.page_source, 'html.parser')
#             driver.quit()
#             listings = []
#             item_class = 'auction-item' # Adjust per site as needed
#             for item in soup.find_all('div', class_=item_class):
#                 lot = parse_lot(item, url)
#                 if lot and is_classic(lot):
#                     lot['source'] = name
#                     listings.append(lot)
#             return listings
#         except Exception as e:
#             print(f"Error scraping {url}: {e}")
#             return []

# def scrape_tradinggarage(base_url="https://www.tradinggarage.com"):
#     listings = []
#     session = requests.Session()
#     session.headers.update({
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
#         'Accept': 'application/json',
#         'Referer': 'https://www.tradinggarage.com/',
#     })
#     endpoints = {
#         'live': 'https://portal.tradinggarage.com/api/v1/auctions?status=live',
#         'coming_soon': 'https://portal.tradinggarage.com/api/v1/auctions?status=coming_soon'
#     }
#     for status, api_url in endpoints.items():
#         try:
#             r = session.get(api_url, timeout=12)
#             if r.status_code != 200:
#                 continue
#             data = r.json()
#             auctions = data.get('data', []) or data.get('auctions', []) or []
#             for auction in auctions:
#                 if auction.get('object_type') != 'vehicle':
#                     continue
#                 title = auction.get('title', 'Unknown Car')
#                 year_str = ''
#                 make = ''
#                 model = ''
#                 m = re.search(r'(\d{4})\s*([a-zA-Z0-9\-() ]+)\s+(.+)', title)
#                 if m:
#                     year_str = m.group(1)
#                     make = m.group(2).strip()
#                     model = m.group(3).strip()
#                 try:
#                     year = int(year_str)
#                 except:
#                     year = 0
#                 price_str = auction.get('last_bid', '0')
#                 auction_date = None
#                 try:
#                     auction_date = parse(auction['auction_end_at'])
#                 except:
#                     pass
#                 images = [auction.get('title_image', '')]
#                 url = f"https://www.tradinggarage.com/products/{auction.get('slug', '')}"
#                 reserve = 'No' if auction.get('no_reserve', False) else 'Yes'
#                 location = 'Online / Melbourne'
#                 description = ''
#                 odometer = ''
#                 lot = {
#                     'source': 'tradinggarage',
#                     'status': auction['status']['name'],
#                     'auction_id': auction['id'],
#                     'title': title,
#                     'year': year,
#                     'make': make,
#                     'model': model,
#                     'odometer': odometer,
#                     'price_range': parse_price(price_str),
#                     'auction_date': auction_date,
#                     'location': location,
#                     'images': images,
#                     'url': url,
#                     'description': description,
#                     'reserve': reserve,
#                     'scrape_time': datetime.now(timezone.utc)
#                 }
#                 if is_classic(lot):
#                     listings.append(lot)
#         except Exception as e:
#             pass
#     return listings

# def scrape_collectingcars():
#     listings = []
#     api_url = "https://dora.production.collecting.com/multi_search"
#     headers = {
#         'x-typesense-api-key': 'aKIufK0SfYHMRp9mUBkZPR7pksehPBZq',
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
#         'Accept': 'application/json',
#         'Content-Type': 'application/json',
#         'Referer': 'https://collectingcars.com/',
#     }
#     base_payload = {
#         "searches": [
#             {
#                 "query_by": "title,productMake,vehicleMake,productYear,tags,lotType,driveSide,location,collectionId,modelId",
#                 "query_by_weights": "9,8,7,6,5,4,3,2,1,0",
#                 "text_match_type": "sum_score",
#                 "sort_by": "rank:asc",
#                 "highlight_full_fields": "*",
#                 "facet_by": "lotType, regionCode, countryCode, saleFormat, noReserve, isBoosted, productMake, vendorType, driveSide, listingStage, tags",
#                 "max_facet_values": 999,
#                 "facet_counts": True,
#                 "facet_stats": True,
#                 "facet_distribution": True,
#                 "facet_return_parent": True,
#                 "collection": "production_cars",
#                 "q": "*",
#                 "filter_by": "listingStage:=[`live`] && countryCode:=[`AU`] && regionCode:=[`APAC`]",
#                 "page": 1,
#                 "per_page": 50
#             }
#         ]
#     }
#     page = 1
#     while True:
#         base_payload["searches"][0]["page"] = page
#         try:
#             response = requests.post(api_url, headers=headers, json=base_payload, timeout=15)
#             if response.status_code != 200:
#                 break
#             data = response.json()
#             if "results" not in data or not data["results"]:
#                 break
#             result = data["results"][0]
#             hits = result.get("hits", [])
#             if not hits:
#                 break
#             for hit in hits:
#                 doc = hit.get("document", {})
#                 if doc.get('lotType') != 'car':
#                     continue
#                 title = doc.get('title', 'Unknown Car')
#                 year_str = doc.get('productYear', '')
#                 try:
#                     year = int(year_str)
#                 except:
#                     year = 0
#                 make = doc.get('productMake', '') or doc.get('vehicleMake', '')
#                 model = doc.get('modelName', '') + ' ' + doc.get('variantName', '').strip()
#                 price_str = doc.get('currentBid', 0)
#                 auction_date = None
#                 try:
#                     auction_date = parse(doc['dtStageEndsUTC'])
#                 except:
#                     pass
#                 images = [doc.get('mainImageUrl', '')]
#                 url = f"https://collectingcars.com/for-sale/{doc.get('slug', '')}"
#                 reserve = 'No' if doc.get('noReserve') == "true" else 'Yes'
#                 location = doc.get('location', 'Australia')
#                 description = '' # No description in data
#                 odometer = doc['features'].get('mileage', '')
#                 transmission = doc['features'].get('transmission', extract_transmission(title))
#                 body_style = extract_body_style(title)
#                 fuel_type = doc['features'].get('fuelType', '')
#                 lot = {
#                     'source': 'collectingcars',
#                     'status': doc['listingStage'],
#                     'auction_id': doc['auctionId'],
#                     'title': title,
#                     'year': year,
#                     'make': make,
#                     'model': model,
#                     'odometer': odometer,
#                     'price_range': parse_price(price_str),
#                     'auction_date': auction_date,
#                     'location': location,
#                     'images': images,
#                     'url': url,
#                     'description': description,
#                     'reserve': reserve,
#                     'body_style': body_style,
#                     'transmission': transmission,
#                     'fuel_type': fuel_type,
#                     'scrape_time': datetime.now(timezone.utc)
#                 }
#                 if is_classic(lot):
#                     listings.append(lot)
#             page += 1
#             time.sleep(1.2)
#         except Exception as e:
#             break
#     return listings

# def scrape_chicane(url='https://www.chicaneauctions.com.au/february-2026-classic-car-auction/'):
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
#                       '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
#     }
#     try:
#         resp = requests.get(url, headers=headers, timeout=20)
#         resp.raise_for_status()
#     except Exception as e:
#         print(f"Error fetching Chicane page: {e}")
#         return []
#     soup = BeautifulSoup(resp.text, 'html.parser')
#     listings = []
#     base_url = 'https://www.chicaneauctions.com.au'
#     for item in soup.select('.promo_box'):
#         try:
#             button = item.select_one('.desc_wrapper .button')
#             link = button if button else item.select_one('.desc_wrapper a')
#             if not link:
#                 continue
#             relative_href = link.get('href', '').strip()
#             if not relative_href:
#                 continue
#             full_url = relative_href if relative_href.startswith('http') else base_url + relative_href
#             if '/sell/' in full_url.lower():
#                 continue
#             title_tag = item.select_one('.desc_wrapper .title')
#             title = title_tag.get_text(strip=True) if title_tag else ''
#             if not title:
#                 continue
#             title_upper = title.upper()
#             if '- OPEN POSITION -' in title_upper or 'STAY TUNED' in title_upper:
#                 continue
#             img_tag = item.select_one('.photo_wrapper img')
#             img_src = None
#             if img_tag:
#                 img_src = img_tag.get('data-src') or img_tag.get('src')
#                 if img_src and img_src.startswith('//'):
#                     img_src = 'https:' + img_src
#             if not img_src or 'upcoming-classic-car-auction-house.png' in img_src:
#                 continue
#             images = [img_src] if img_src else []
#             lot_num = None
#             m = re.search(r'(?:lot[-_\s]*)(\d+)', full_url, re.IGNORECASE)
#             if m:
#                 lot_num = m.group(1)
#             if not lot_num:
#                 m = re.search(r'(?:lot|Lot|LOT)\s*(\d+)', title, re.IGNORECASE)
#                 if m:
#                     lot_num = m.group(1)
#             year = None
#             make = ''
#             model = ''
#             m = re.match(r'^(\d{4})\s+([A-Za-z0-9\-]+(?:\s+[A-Za-z0-9\-]+)*?)(?:\s+(.+?))?(?:\s*-|$)', title.strip())
#             if m:
#                 try:
#                     year = int(m.group(1))
#                 except:
#                     pass
#                 make = (m.group(2) or '').strip()
#                 model = (m.group(3) or '').strip()
#             if not year:
#                 ym = re.search(r'\b(19\d{2}|20\d{2})\b', title)
#                 if ym:
#                     year = int(ym.group(1))
#             location = {
#                 'city': 'Melbourne',
#                 'state': 'VIC',
#                 'country': 'Australia'
#             }
#             lot = {
#                 'source': 'chicaneauctions',
#                 'auction_id': lot_num or title.lower().replace(' ', '-').replace('--', '-'),
#                 'title': title,
#                 'url': full_url,
#                 'year': year,
#                 'make': make,
#                 'model': model,
#                 'vehicle': {
#                     'year': year,
#                     'make': make,
#                     'model': model,
#                 },
#                 'price': {
#                     'current': None,  # not shown on pre-catalogue
#                     'reserve': 'Unknown',
#                 },
#                 'auction_end': None,  # not shown yet
#                 'location': location,
#                 'images': images,
#                 'condition': {
#                     'comment': title,  # can be improved later from detail page
#                 },
#                 'status': 'upcoming',
#                 'scrape_time': datetime.now(timezone.utc).isoformat(),
#             }
#             if is_classic(lot):
#                 listings.append(lot)
#         except Exception as e:
#             print(f"Error parsing one Chicane promo_box: {e}")
#             continue
#     return listings

# def scrape_lloydsonline(url='https://www.lloydsonline.com.au/AuctionLots.aspx?stype=0&stypeid=0&cid=410&smode=0'):
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
#     }
#     try:
#         resp = requests.get(url, headers=headers, timeout=20)
#         if resp.status_code != 200:
#             print(f"Lloyds returned {resp.status_code}")
#             return []
#         html_content = resp.text
#     except Exception as e:
#         print(f"Error fetching Lloyds: {e}")
#         return []
#     soup = BeautifulSoup(html_content, 'html.parser')
#     listings = []
#     base_url = 'https://www.lloydsonline.com.au'
#     for item in soup.select('.gallery_item.lot_list_item'):
#         try:
#             link = item.select_one('a[href^="LotDetails.aspx"]')
#             relative_href = link.get('href') if link else None
#             full_url = None
#             if relative_href:
#                 full_url = base_url + '/' + relative_href.lstrip('/')
#             lot_num_elem = item.select_one('.lot_num')
#             lot_num = lot_num_elem.text.strip() if lot_num_elem else None
#             img_tag = item.select_one('.lot_img img')
#             img_src = None
#             if img_tag and img_tag.has_attr('src'):
#                 img_src = img_tag['src'].strip()
#                 if img_src.startswith('//'):
#                     img_src = 'https:' + img_src
#             images = [img_src] if img_src else []
#             desc_elem = item.select_one('.lot_desc')
#             title = desc_elem.get_text(strip=True) if desc_elem else ''
#             year = None
#             make = ''
#             model = ''
#             m = re.match(r'^(\d{4})\s+(.+?)\s+(.+?)(?:\s+|$)', title)
#             if m:
#                 try:
#                     year = int(m.group(1))
#                 except ValueError:
#                     pass
#                 make = m.group(2).strip()
#                 model = m.group(3).strip()
#             bid_tag = item.select_one('.lot_cur_bid span, .lot_bidding span')
#             current_bid_str = bid_tag.get_text(strip=True) if bid_tag else '0'
#             current_bid = None
#             try:
#                 current_bid = float(re.sub(r'[^\d.]', '', current_bid_str))
#             except (ValueError, TypeError):
#                 pass
#             time_rem_tag = item.select_one('[data-seconds_rem]')
#             seconds_rem = 0
#             if time_rem_tag and time_rem_tag.has_attr('data-seconds_rem'):
#                 try:
#                     seconds_rem = int(time_rem_tag['data-seconds_rem'])
#                 except ValueError:
#                     pass
#             auction_end = datetime.now(timezone.utc) + timedelta(seconds=seconds_rem) if seconds_rem > 0 else None
#             location_img = item.select_one('.auctioneer-location img')
#             state_src = location_img.get('src', '').split('/')[-1] if location_img else ''
#             state_map = {
#                 's_1.png': 'ACT', 's_2.png': 'NT', 's_3.png': 'NSW',
#                 's_4.png': 'QLD', 's_5.png': 'SA', 's_6.png': 'TAS',
#                 's_7.png': 'WA', 's_8.png': 'VIC',
#             }
#             state = state_map.get(state_src, '')
#             location = {'state': state}
#             unreserved = item.select_one('.sash.ribbon-blue')
#             reserve = 'No' if unreserved and 'UNRESERVED' in (unreserved.get_text(strip=True) or '').upper() else 'Yes'
#             vehicle = {
#                 'year': year,
#                 'make': make,
#                 'model': model,
#             }
#             price = {
#                 'current': current_bid,
#             }
#             condition = {
#                 'comment': title,
#             }
#             lot = {
#                 'source': 'lloydsonline',
#                 'auction_id': lot_num,  # or use data-lot_id if available
#                 'title': title,
#                 'url': full_url,
#                 'year': year,
#                 'make': make,
#                 'model': model,
#                 'vehicle': vehicle,
#                 'price': price,
#                 'auction_end': auction_end,
#                 'location': location,
#                 'images': images,
#                 'condition': condition,
#                 'reserve': reserve,
#                 'status': 'live' if seconds_rem > 0 else 'ended',
#                 'scrape_time': datetime.now(timezone.utc),
#             }
#             if is_classic(lot):
#                 listings.append(lot)
#         except Exception as e:
#             print(f"Error parsing Lloyds lot: {str(e)}")
#     return listings

# def scrape_carbids_api():
#     listings = []
#     session = requests.Session()
#     session.headers.update({
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
#         'Accept': 'application/json, text/plain, */*',
#         'X-Requested-With': 'XMLHttpRequest',
#         'Referer': 'https://carbids.com.au/',
#         'Origin': 'https://carbids.com.au',
#     })
#     try:
#         home = session.get("https://carbids.com.au/t/unique-and-classic-car-auctions")
#         soup = BeautifulSoup(home.text, 'html.parser')
#         token_input = soup.find('input', {'name': '__RequestVerificationToken'})
#         if token_input and token_input.get('value'):
#             session.headers['__RequestVerificationToken'] = token_input['value']
#     except:
#         pass
#     page = 0
#     while True:
#         payload = {
#             "top": 96,
#             "skip": page * 96,
#             "sort": {"aucClose": "asc"},
#             "tagName": "Unique and Classic Car Auctions",
#             "filter": {"Display": True}
#         }
#         try:
#             resp = session.post(
#                 "https://carbids.com.au/Search/Tags",
#                 json=payload,
#                 timeout=20
#             )
#             if resp.status_code != 200:
#                 print(f"Carbids API returned {resp.status_code}")
#                 break
#             data = resp.json()
#             auctions = data.get("auctions", [])
#             if not auctions:
#                 break
#             for auc in auctions:
#                 title = auc.get("aucTitle", "").strip()
#                 title_text = auc.get("aucTitleText", title).strip()
#                 short_title = auc.get("aucTitleShortText", title).strip()
#                 year = None
#                 make = ""
#                 model = ""
#                 m = re.match(r'^(\d{1,2}/)?(\d{4})\s+(.+?)\s+(.+?)(?:\s+|$)', title_text)
#                 if m:
#                     year_str = m.group(2)
#                     make = m.group(3).strip()
#                     model = m.group(4).strip()
#                     try:
#                         year = int(year_str)
#                     except:
#                         year = None
#                 if not year and auc.get("aucYear"):
#                     try:
#                         year = int(auc["aucYear"])
#                     except:
#                         pass
#                 make = auc.get("aucMake", make).strip()
#                 model = auc.get("aucModel", model).strip()
#                 current_bid = auc.get("aucCurrentBid", 0.0)
#                 starting_bid = auc.get("aucStartingBid", 1.0)
#                 price_info = {
#                     "current": float(current_bid) if current_bid else None,
#                     "starting": float(starting_bid) if starting_bid else None,
#                     "increment": auc.get("aucBidIncrement", 0.0),
#                     "buyers_premium_text": auc.get("aucBPText", ""),
#                     "gst_note": auc.get("isGstApplicableWording", "")
#                 }
#                 end_date_str = auc.get("aucCloseUtc")
#                 auction_end = None
#                 if end_date_str:
#                     try:
#                         auction_end = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
#                     except:
#                         try:
#                             auction_end = parse(end_date_str)
#                         except:
#                             pass
#                 location = {
#                     "city": auc.get("aucCity", ""),
#                     "state": auc.get("aucState", ""),
#                     "address": auc.get("aucAddressLocation", ""),
#                     "pickup": auc.get("aucPickupAvailable", False),
#                     "freight": auc.get("aucFreightAvailable", False),
#                     "freight_limits": auc.get("aucItemFreightLimits", "")
#                 }
#                 vehicle = {
#                     "year": year,
#                     "make": make,
#                     "model": model,
#                     "odometer_km": auc.get("aucOdometerNumber"),
#                     "odometer_display": auc.get("aucOdometer", ""),
#                     "transmission": auc.get("aucTransmission"),
#                     "fuel_type": auc.get("aucFuelType"),
#                     "engine_capacity": auc.get("aucCapacity"),
#                     "cylinders": auc.get("aucCylinder"),
#                     "drivetrain": auc.get("aucDrv"),
#                 }
#                 images = []
#                 base = auc.get("aucCarsThumbnailUrl", auc.get("aucThumbnailUrl", ""))
#                 if base:
#                     images.append(base)
#                 for size in ["small", "medium", "large"]:
#                     key = f"aucCars{size.capitalize()}ThumbnailUrl"
#                     if auc.get(key):
#                         images.append(auc[key])
#                 medium_list = auc.get("aucMediumThumbnailUrlList", [])
#                 images.extend([url for url in medium_list if url])
#                 condition = {
#                     "body": auc.get("aucBodyCondition"),
#                     "paint": auc.get("aucPaintCondition"),
#                     "features_text": auc.get("aucFeaturesText"),
#                     "key_facts": auc.get("aucKeyFactsText"),
#                     "comment": auc.get("aucComment"),
#                     "service_history": auc.get("aucServiceHistory"),
#                 }
#                 lot = {
#                     "source": "carbids",
#                     "auction_id": auc.get("aucID"),
#                     "reference_number": auc.get("aucReferenceNo"),
#                     "title": title_text,
#                     "short_title": short_title,
#                     "url": "https://carbids.com.au/" + auc.get("AucDetailsUrlLink", "").lstrip("/"),
#                     "year": year,
#                     "make": make,
#                     "model": model,
#                     "vehicle": vehicle,
#                     "price": price_info,
#                     "auction_end": auction_end,
#                     "location": location,
#                     "images": images[:8], # limit to 8 for storage
#                     "condition": condition,
#                     "reserve": "Yes", # currently no reserve field → assume Yes
#                     "status": "live", # we only get live auctions here
#                     "scrape_time": datetime.now(timezone.utc),
#                 }
#                 if is_classic(lot):
#                     listings.append(lot)
#             page += 1
#             time.sleep(1.3) # polite delay
#         except Exception as e:
#             print("Error in carbids API loop:", str(e))
#             break
#     return listings

# def scrape_carbids(base_url):
#     listings_api = scrape_carbids_api()
#     combined = listings_api
#     seen_urls = set()
#     unique = []
#     for lot in combined:
#         u = lot.get("url")
#         if u and u not in seen_urls:
#             seen_urls.add(u)
#             unique.append(lot)
#     return unique

# def scrape_bennetts(base_url="https://www.bennettsclassicauctions.com.au"):
#     pages = [base_url, base_url + '/off-site.php']
#     all_listings = []
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
#     }
#     for page_url in pages:
#         try:
#             resp = requests.get(page_url, headers=headers, timeout=20)
#             resp.raise_for_status()
#             soup = BeautifulSoup(resp.text, 'html.parser')
#             sitename = soup.find('div', id='sitename')
#             h3 = sitename.find('h3') if sitename else None
#             auction_text = h3.text.strip() if h3 else ''
#             date_match = re.search(r'(\d{1,2}[ST|ND|RD|TH]{0,2} \w+ \d{4})', auction_text.upper())
#             time_match = re.search(r'@ (\d{1,2}[AP]M)', auction_text.upper())
#             auction_date_str = ''
#             if date_match:
#                 date_str = re.sub(r'([ST|ND|RD|TH])', '', date_match.group(1))
#                 auction_date_str += date_str
#             if time_match:
#                 auction_date_str += ' ' + time_match.group(1)
#             auction_date = None
#             try:
#                 auction_date = parse(auction_date_str)
#             except:
#                 pass
#             sections = soup.find_all('div', class_='clear')
#             for section in sections:
#                 column = section.find('div', class_='column column-600 column-left')
#                 if column:
#                     h3_cat = column.find('h3')
#                     category = h3_cat.text.strip() if h3_cat else ''
#                     table = column.find('table')
#                     if table:
#                         tbody = table.find('tbody')
#                         trs = tbody.find_all('tr') if tbody else table.find_all('tr')
#                         for tr in trs[1:]:  # Skip header
#                             tds = tr.find_all('td')
#                             if len(tds) >= 7:  # Ensure enough columns
#                                 photo_td = tds[0]
#                                 a = photo_td.find('a')
#                                 detail_url = base_url + '/' + a['href'].lstrip('/') if a else ''
#                                 img = photo_td.find('img')
#                                 image_src = base_url + '/' + img['src'].lstrip('/') if img and img['src'].startswith('images') else (img['src'] if img else '')
#                                 make = tds[1].text.strip()
#                                 stock_model = tds[2].text.strip()
#                                 parts = stock_model.split('/')
#                                 stock_ref = parts[0].strip() if parts else ''
#                                 model = parts[1].strip() if len(parts) > 1 else stock_model
#                                 year_str = tds[3].text.strip()
#                                 try:
#                                     year = int(year_str)
#                                 except:
#                                     year = 0
#                                 options = tds[4].text.strip()
#                                 location_td = tds[5]
#                                 location = location_td.text.strip().replace('\n', '').replace('br /', '')
#                                 lot = {
#                                     'source': 'bennettsclassicauctions',
#                                     'make': make,
#                                     'model': model,
#                                     'year': year,
#                                     'price_range': None,
#                                     'auction_date': auction_date,
#                                     'location': location,
#                                     'images': [image_src] if image_src else [],
#                                     'url': detail_url,
#                                     'description': options,
#                                     'reserve': 'Yes',
#                                     'body_style': extract_body_style(options),
#                                     'transmission': extract_transmission(options),
#                                     'scrape_time': datetime.now(timezone.utc)
#                                 }
#                                 if is_classic(lot):
#                                     all_listings.append(lot)
#         except Exception as e:
#             print(f"Error scraping Bennetts ({page_url}): {str(e)}")
#     return all_listings

# def scrape_burnsandco(base_url="https://burnsandcoauctions.com.au"):
#     pages = [base_url + '/current-auctions/', base_url + '/upcoming-auctions/']
#     all_listings = []
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
#     }
#     for page_url in pages:
#         try:
#             resp = requests.get(page_url, headers=headers, timeout=20)
#             resp.raise_for_status()
#             soup = BeautifulSoup(resp.text, 'html.parser')
#             articles = soup.find_all('article', class_='regular masonry-blog-item')
#             for article in articles:
#                 img_link = article.find('a', class_='img-link')
#                 detail_url = img_link['href'] if img_link else ''
#                 img = img_link.find('img') if img_link else None
#                 image_src = img['src'] if img else ''
#                 meta_category = article.find('span', class_='meta-category')
#                 category = meta_category.text.strip() if meta_category else ''
#                 date_item = article.find('span', class_='date-item')
#                 auction_date_str = date_item.text.strip() if date_item else ''
#                 auction_date = None
#                 try:
#                     auction_date = parse(auction_date_str)
#                 except:
#                     pass
#                 title_a = article.find('h3', class_='title').find('a') if article.find('h3', class_='title') else None
#                 title = title_a.text.strip() if title_a else ''
#                 excerpt = article.find('div', class_='excerpt').text.strip() if article.find('div', class_='excerpt') else ''
#                 place = article.find('p', class_='place').text.strip() if article.find('p', class_='place') else ''
#                 bid_links = article.find_all('p', class_='registration_bidding_link')
#                 for bid_p in bid_links:
#                     bid_a = bid_p.find('a')
#                     bid_url = bid_a['href'] if bid_a else ''
#                     catalogue_lots = scrape_catalogue(bid_url)
#                     for cat_lot in catalogue_lots:
#                         cat_lot['auction_date'] = auction_date or cat_lot.get('auction_date')
#                         cat_lot['location'] = place or cat_lot.get('location')
#                         cat_lot['source'] = 'burnsandco'
#                         all_listings.append(cat_lot)
#         except Exception as e:
#             print(f"Error scraping Burns and Co ({page_url}): {str(e)}")
#     return all_listings

# def scrape_seven82motors():
#     listings = []
#     auction_slug = "march-29th-2026"
#     api_url = f"https://seven82-json-sb.manage.auction/listings/auctions/{auction_slug}?amt=100"
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
#                       '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
#         'Accept': 'application/json',
#         'Referer': 'https://www.seven82motors.com.au/',
#     }
#     try:
#         resp = requests.get(api_url, headers=headers, timeout=20)
#         resp.raise_for_status()
#         data = resp.json()
#         auction_title = data.get("heading", "Unknown Auction Date")
#         auction_date = None
#         date_str_candidates = [
#             auction_title,
#             data.get("breadcrumbs", [{}])[0].get("title", ""),
#             f"{auction_title} 2026",
#             auction_slug.replace("-", " ").title()
#         ]
#         for candidate in date_str_candidates:
#             if not candidate:
#                 continue
#             try:
#                 auction_date = parse(candidate, fuzzy=True, dayfirst=False)
#                 if auction_date.year >= 2025:
#                     break
#             except:
#                 continue
#         if not auction_date:
#             auction_date = datetime.now(timezone.utc) + timedelta(days=60)
#         items = data.get("items", [])
#         for item in items:
#             if item.get("dummy_lot", 0) == 1:
#                 continue
#             title = (item.get("title") or "").strip()
#             if not title:
#                 continue
#             if any(phrase in title.upper() for phrase in [
#                 "SELL YOUR CAR", "CONSIGN", "REGISTER AND BID", "LEARN HOW TO"
#             ]):
#                 continue
#             year = None
#             make = ""
#             model = ""
#             clean_title = re.sub(
#                 r'^(NO RESERVE!?\s*|RARE\s*|FULLY RESTORED\s*|CUSTOM\s*)',
#                 '', title, flags=re.IGNORECASE
#             ).strip()
#             m = re.match(r'^(\d{4})\s+(.+?)(?:\s+(.+?))?(?:\s+|$)', clean_title)
#             if m:
#                 try:
#                     year = int(m.group(1))
#                 except:
#                     pass
#                 make_model_part = (m.group(2) or "").strip()
#                 extra = (m.group(3) or "").strip()
#                 parts = make_model_part.split(maxsplit=1)
#                 if parts:
#                     make = parts[0].strip()
#                     if len(parts) > 1:
#                         model = parts[1].strip()
#                     model = f"{model} {extra}".strip()
#             reserve = "No" if "NO RESERVE" in title.upper() else "Yes"
#             images = []
#             featured = item.get("media_featured", [])
#             if isinstance(featured, list):
#                 for img_obj in featured:
#                     if isinstance(img_obj, dict):
#                         src = img_obj.get("src")
#                         if src and "catalog/" in src:
#                             clean_src = src.lstrip('/')
#                             full_url = f"https://seven82motors.mymedia.delivery/{clean_src}"
#                             if full_url not in images:
#                                 images.append(full_url)
#             main_img = item.get("image")
#             if main_img and "catalog/" in main_img:
#                 clean_main = main_img.lstrip('/')
#                 full_main = f"https://seven82motors.mymedia.delivery/{clean_main}"
#                 if full_main not in images:
#                     images.insert(0, full_main)
#             seen = set()
#             clean_images = []
#             for url in images:
#                 if url and url not in seen:
#                     seen.add(url)
#                     if not any(x in url.lower() for x in ["thumb", "small", "placeholder", "watermark"]):
#                         clean_images.append(url)
#             images = clean_images[:12]
#             is_coming_soon = False
#             coming_soon_data = item.get("coming_soon", [])
#             if isinstance(coming_soon_data, list):
#                 for entry in coming_soon_data:
#                     if isinstance(entry, dict):
#                         if entry.get("settings", {}).get("coming_soon") in (True, "1", 1, "true"):
#                             is_coming_soon = True
#                             break
#             lot_path = item.get('path', '').lstrip('/')
#             lot_url = f"https://www.seven82motors.com.au/lot/{lot_path}" if lot_path else ""
#             lot = {
#                 'source': 'seven82motors',
#                 'status': 'upcoming',
#                 'auction_id': item.get("id"),
#                 'lot_number': item.get("number"),
#                 'title': title,
#                 'year': year,
#                 'make': make,
#                 'model': model,
#                 'odometer': None,  # detail page only
#                 'price_range': None,  # not in list view
#                 'auction_date': auction_date,
#                 'location': "Brisbane, QLD (Online)",
#                 'images': images,
#                 'url': lot_url,
#                 'description': (item.get("description_short") or "").strip(),
#                 'reserve': reserve,
#                 'body_style': None,
#                 'transmission': None,
#                 'fuel_type': None,
#                 'scrape_time': datetime.now(timezone.utc),
#                 'coming_soon': is_coming_soon,
#                 'buyers_premium_pct': 8.8,
#                 'auction_title': auction_title,
#                 'raw_filters': item.get("filters", {}),
#             }
#             if is_classic(lot):
#                 listings.append(lot)
#     except Exception as e:
#         print(f"[seven82motors] Error scraping {auction_slug}: {e}")
#     return listings

# def scrape_catalogue(catalogue_url):
#     listings = []
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
#     }
#     try:
#         resp = requests.get(catalogue_url, headers=headers, timeout=20)
#         resp.raise_for_status()
#         soup = BeautifulSoup(resp.text, 'html.parser')
#         table = soup.find('table')  # Or find('table', class_='catalogue-table') if specific class
#         if table:
#             trs = table.find_all('tr')
#             for tr in trs[1:]:  # Skip header row
#                 tds = tr.find_all('td')
#                 if len(tds) < 4:
#                     continue
#                 lot_number = tds[0].text.strip()
#                 desc_td = tds[1]
#                 desc = desc_td.text.strip()
#                 match = re.match(r'(\d{4})? ?(.*?) (.*)', desc)
#                 year_str = match.group(1) if match and match.group(1) else ''
#                 try:
#                     year = int(year_str)
#                 except:
#                     year = 0
#                 make = match.group(2) if match else ''
#                 model = match.group(3) if match else desc
#                 images = [urljoin(catalogue_url, img['src']) for img in tr.find_all('img') if 'src' in img.attrs]
#                 detail_a = desc_td.find('a')
#                 detail_url = urljoin(catalogue_url, detail_a['href']) if detail_a else ''
#                 current_bid = tds[2].text.strip()
#                 lot = {
#                     'lot_number': lot_number,
#                     'make': make,
#                     'model': model,
#                     'year': year,
#                     'price_range': parse_price(current_bid),
#                     'auction_date': None,
#                     'location': None,
#                     'images': images,
#                     'url': detail_url,
#                     'description': desc,
#                     'reserve': 'Yes',
#                     'body_style': extract_body_style(desc),
#                     'transmission': extract_transmission(desc),
#                     'scrape_time': datetime.now(timezone.utc)
#                 }
#                 if is_classic(lot):
#                     listings.append(lot)
#     except Exception as e:
#         print(f"Error scraping catalogue ({catalogue_url}): {str(e)}")
#     return listings

# def parse_lot(item, url):
#     try:
#         description = item.find('p', class_='desc') or item.find('div', class_='description')
#         description_text = description.text.strip() if description else ''
#         year_elem = item.find('span', class_='year') or item.find('h3')
#         year_str = year_elem.text.strip() if year_elem else '0'
#         try:
#             year = int(year_str)
#         except:
#             year = 0
#         make_elem = item.find('span', class_='make') or item.find('h2')
#         model_elem = item.find('span', class_='model')
#         price_elem = item.find('span', class_='estimate') or item.find('div', class_='price')
#         price_str = price_elem.text.strip() if price_elem else None
#         date_elem = item.find('span', class_='date')
#         location_elem = item.find('span', class_='location')
#         link_elem = item.find('a', class_='lot-link') or item.find('a')
#         lot = {
#             'make': make_elem.text.strip() if make_elem else None,
#             'model': model_elem.text.strip() if model_elem else None,
#             'year': year,
#             'price_range': parse_price(price_str),
#             'auction_date': parse_date(date_elem.text.strip()) if date_elem else None,
#             'location': location_elem.text.strip() if location_elem else 'Online',
#             'images': [img['src'] for img in item.find_all('img', class_='thumbnail')][:6],
#             'url': link_elem['href'] if link_elem else url,
#             'description': description_text,
#             'reserve': 'No' if 'no reserve' in description_text.lower() else 'Yes',
#             'body_style': extract_body_style(description_text),
#             'transmission': extract_transmission(description_text),
#             'scrape_time': datetime.now(timezone.utc)
#         }
#         return lot
#     except:
#         return None

# def parse_date(date_str):
#     try:
#         return parse(date_str)
#     except:
#         return None

# def extract_body_style(desc):
#     lower_desc = desc.lower()
#     styles = ['coupe', 'convertible', 'sedan', 'wagon', 'ute', 'truck']
#     for style in styles:
#         if style in lower_desc:
#             return style.capitalize()
#     return None

# def extract_transmission(desc):
#     lower_desc = desc.lower()
#     if 'manual' in lower_desc:
#         return 'Manual'
#     if 'auto' in lower_desc or 'automatic' in lower_desc:
#         return 'Automatic'
#     return None

# def is_classic(lot):
#     year = lot.get('year')
#     if year is None or not isinstance(year, (int, float)):
#         text = (lot.get('title', '') + ' ' + lot.get('description', '')).lower()
#         has_classic_hint = any(word in text for word in [
#             'classic', 'muscle', 'vintage', 'hot rod', 'restored', 'collector',
#             'holden', 'falcon gt', 'monaro', 'charger', 'mustang', 'corvette'
#         ])
#         return has_classic_hint
#     if year < 2005:
#         return True
#     text = (lot.get('title', '') + ' ' + lot.get('description', '')).lower()
#     modern_classic_keywords = [
#         'hellcat', 'demon', 'supercharged', 'stroker', 'r8', 'gts-r', 'boss 302',
#         'shelby', 'a9x', 'fpv', 'gtr', 'torana', 'monaro'
#     ]
#     return any(kw in text for kw in modern_classic_keywords)

# def normalize_auction_date(ad):
#     if not ad:
#         return None
#     if isinstance(ad, datetime):
#         return ad
#     if isinstance(ad, str):
#         try:
#             return parse(ad)
#         except:
#             return None
#     try:
#         return parse(str(ad))
#     except:
#         return None

# # Scrape all and store in DB (sync version)
# def scrape_all():
#     all_lots = []
#     scrape_start = datetime.now(timezone.utc)
#     for source in SOURCES:
#         lots = scrape_site(source)
#         all_lots.extend(lots)
    
#     for lot in all_lots:
#         lot['scrape_time'] = datetime.now(timezone.utc)
#         lot['auction_date'] = normalize_auction_date(lot.get('auction_date'))
#         if not lot.get('url'):
#             lot['url'] = f"{lot.get('source','unknown')}/{uuid.uuid4()}"
#         sync_lots_collection.update_one(
#             {'url': lot['url']},
#             {'$set': lot, '$setOnInsert': {'first_scraped': scrape_start}},
#             upsert=True
#         )
    
#     now = datetime.now(timezone.utc)
#     ended = list(sync_lots_collection.find({'auction_date': {'$lt': now}}))
#     for end in ended:
#         house = end['source']
#         prem = house_premiums.get(house, 0.15)
#         hammer = end.get('price_range', {}).get('high', 0)
#         total = hammer * (1 + prem)
#         sold_doc = dict(end)
#         sold_doc['hammer_price'] = hammer
#         sold_doc['buyers_premium'] = prem * 100
#         sold_doc['total_price'] = total
#         sync_sold_collection.insert_one(sold_doc)
#         sync_lots_collection.delete_one({'_id': end['_id']})
    
#     two_years_ago = now - timedelta(days=730)
#     sync_sold_collection.delete_many({'auction_date': {'$lt': two_years_ago}})

# # Scheduler for scraping
# scheduler = BackgroundScheduler()
# scheduler.add_job(scrape_all, 'interval', hours=1)
# scheduler.start()

# # Vehicle Fetching using DB (scraped data)
# # async def fetch_vehicles(path: str, criteria: Dict) -> list:
# #     if path != "preowned":
# #         return []  # For "new", no data from sources
    
# #     query = {}
# #     if "min_price" in criteria:
# #         query["price_range.low"] = {"$gte": criteria["min_price"]}
# #     if "max_price" in criteria:
# #         query["price_range.high"] = {"$lte": criteria["max_price"]}
# #     if "interest" in criteria:
# #         interest = criteria["interest"]
# #         query["$or"] = [
# #             {"make": {"$regex": interest, "$options": "i"}},
# #             {"model": {"$regex": interest, "$options": "i"}},
# #             {"title": {"$regex": interest, "$options": "i"}},
# #             {"description": {"$regex": interest, "$options": "i"}}
# #         ]
    
# #     vehicles = await lots_collection.find(query).limit(8).to_list(8)
# #     return [dict(v, _id=str(v["_id"])) for v in vehicles]


# async def fetch_vehicles(path: str, criteria: Dict, page: int, page_size: int):
#     if path != "preowned":
#         return [], 0

#     query = {}

#     if "min_price" in criteria:
#         query["price_range.low"] = {"$gte": criteria["min_price"]}

#     if "max_price" in criteria:
#         query["price_range.high"] = {"$lte": criteria["max_price"]}

#     if "interest" in criteria:
#         interest = criteria["interest"]
#         query["$or"] = [
#             {"make": {"$regex": interest, "$options": "i"}},
#             {"model": {"$regex": interest, "$options": "i"}},
#             {"title": {"$regex": interest, "$options": "i"}},
#             {"description": {"$regex": interest, "$options": "i"}}
#         ]

#     # Pagination logic
#     skip = (page - 1) * page_size

#     total = await lots_collection.count_documents(query)

#     cursor = (
#         lots_collection
#         .find(query)
#         .skip(skip)
#         .limit(page_size)
#     )

#     vehicles = await cursor.to_list(length=page_size)

#     return [dict(v, _id=str(v["_id"])) for v in vehicles], total
# # xAI API Integration for Conversational AI
# async def generate_ai_response(state: ConversationState, user_message: str) -> str:
#     system_prompt = f"""
#     You are an AI car finder for Australian users. Follow the project scope strictly.
#     Handle onboarding, language selection, preowned/new paths, financing with LVR, resumability, personalization, empathy.
#     Be inclusive, compliant with ACL, NCCP, APP. Provide indicative guidance only.
#     Support languages: English, Mandarin, Arabic, Hindi, etc. Respond in selected language.
#     Use name if available. Adapt tone.
#     For finance: Use LVR calculation - call internal API if needed (but simulate here).
#     Present 4-8 vehicle matches from inventory.
#     Allow exploration, comparison, refinement.
#     On selection: Verify, collect docs (prompt for upload), handoff to broker.
#     Additional: Trade-in, insurance, tips.
#     Escalate to human if complex.
#     Allow language switching.
#     State: {state.dict()}
#     If resuming: Welcome back and reference last discussion.
#     """
#     messages = [
#         {"role": "system", "content": system_prompt},
#         *state.history,
#         {"role": "user", "content": user_message}
#     ]
#     url = "https://api.x.ai/v1/chat/completions"
#     headers = {
#         "Authorization": f"Bearer {XAI_API_KEY}",
#         "Content-Type": "application/json"
#     }
#     data = {
#         "model": "grok-3",
#         "messages": messages,
#         "temperature": 0.7,
#         "max_tokens": 500
#     }
#     response = requests.post(url, headers=headers, json=data)
#     if response.status_code == 200:
#         ai_reply = response.json()["choices"][0]["message"]["content"]
#         state.history.append({"role": "user", "content": user_message})
#         state.history.append({"role": "assistant", "content": ai_reply})
#         return ai_reply
#     raise HTTPException(status_code=500, detail="AI response failed")

# # Web Chat Endpoint (for chatbot widget)
# @app.post("/chat")
# async def web_chat(message: Message):
#     state_doc = await conversations.find_one({"phone": message.phone})
#     if state_doc:
#         state = ConversationState(**state_doc)
#         state.last_message_time = state.last_message_time.replace(tzinfo=timezone.utc) if state.last_message_time.tzinfo is None else state.last_message_time
#         if (datetime.now(timezone.utc) - state.last_message_time).total_seconds() > 3600:
#             welcome_back = f"Welcome back, {state.name or 'there'}! Last time we were looking at {state.path or 'car options'}."
#             message.body = welcome_back + " " + message.body
#     else:
#         state = ConversationState(phone=message.phone)
    
#     try:
#         reply = await generate_ai_response(state, message.body)
#     except Exception as e:
#         reply = "Sorry, something went wrong. Please try again."

#     state.last_message_time = datetime.now(timezone.utc)
#     await conversations.replace_one({"phone": message.phone}, state.dict(), upsert=True)

#     if "handoff" in reply.lower() or "broker" in reply.lower():
#         lead = {
#             "phone": message.phone,
#             "state": state.dict(),
#             "timestamp": datetime.now(timezone.utc)
#         }
#         await leads.insert_one(lead)
#         print("Handoff to broker:", lead)
#         reply += " Connecting you to a broker soon."

#     return {"reply": reply}

# @app.post("/lvr", response_model=Dict)
# def get_lvr(input: LVRInput):
#     return calculate_lvr(input.vehicle_value, input.loan_amount)

# # @app.get("/vehicles")
# # async def get_vehicles(path: str, budget_min: Optional[float] = None, budget_max: Optional[float] = None, interest: Optional[str] = None):
# #     criteria = {}
# #     if budget_min:
# #         criteria["min_price"] = budget_min
# #     if budget_max:
# #         criteria["max_price"] = budget_max
# #     if interest:
# #         criteria["interest"] = interest
# #     vehicles = await fetch_vehicles(path, criteria)
# #     return {"vehicles": vehicles}
# @app.get("/vehicles")
# async def get_vehicles(
#     path: str,
#     budget_min: Optional[float] = None,
#     budget_max: Optional[float] = None,
#     interest: Optional[str] = None,
#     page: int = Query(1, ge=1),
#     page_size: int = Query(8, ge=1, le=50)
# ):
#     criteria = {}

#     if budget_min is not None:
#         criteria["min_price"] = budget_min
#     if budget_max is not None:
#         criteria["max_price"] = budget_max
#     if interest:
#         criteria["interest"] = interest

#     vehicles, total = await fetch_vehicles(path, criteria, page, page_size)

#     return {
#         "page": page,
#         "page_size": page_size,
#         "total_results": total,
#         "total_pages": (total + page_size - 1) // page_size,
#         "vehicles": vehicles
#     }
# @app.post("/upload/{phone}")
# async def upload_document(phone: str, file: UploadFile = File(...)):
#     if not await conversations.find_one({"phone": phone}):
#         raise HTTPException(403, "No active session")
    
#     os.makedirs(f"uploads/{phone}", exist_ok=True)
#     file_path = f"uploads/{phone}/{file.filename}"
#     with open(file_path, "wb") as f:
#         f.write(await file.read())
    
#     meta = {
#         "phone": phone,
#         "file_name": file.filename,
#         "path": file_path,
#         "timestamp": datetime.now(timezone.utc)
#     }
#     await uploads.insert_one(meta)
#     return {"status": "uploaded", "file": file.filename}

# @app.get("/leads")
# async def get_leads():
#     lead_list = []
#     async for lead in leads.find():
#         lead["_id"] = str(lead["_id"])
#         lead_list.append(lead)
#     return {"leads": lead_list}

# @app.get("/")
# def health():
#     return {"status": "healthy"}

# @app.post("/scrape")
# def scrape_endpoint():
#     scrape_all()
#     return {"message": "Scraping completed"}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)
# import os
# from dotenv import load_dotenv
# from fastapi import FastAPI, Request, UploadFile, File, HTTPException
# from fastapi.responses import JSONResponse
# from motor.motor_asyncio import AsyncIOMotorClient
# from pydantic import BaseModel
# from fastapi import Query

# from typing import Optional, Dict, Any
# import requests
# import datetime
# from bson import ObjectId
# from fastapi.openapi.utils import get_openapi
# from bs4 import BeautifulSoup
# import re
# import time
# import uuid
# from datetime import datetime, timezone, timedelta
# from dateutil.parser import parse
# import platform
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.chrome.service import Service
# from webdriver_manager.chrome import ChromeDriverManager
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from apscheduler.schedulers.background import BackgroundScheduler
# from math import ceil
# from urllib.parse import urljoin
# import pymongo
# from fastapi.middleware.cors import CORSMiddleware
# load_dotenv()

# # Environment Variables
# XAI_API_KEY = os.getenv("XAI_API_KEY")
# REDBOOK_API_KEY = os.getenv("REDBOOK_API_KEY")  # Kept but not used
# MONGO_URI = os.getenv("MONGO_URI")

# # FastAPI App
# app = FastAPI(title="Best Next Car Backend - Chatbot Focus")
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
# # Custom OpenAPI schema (optional, for customization)
# def custom_openapi():
#     if app.openapi_schema:
#         return app.openapi_schema
#     openapi_schema = get_openapi(
#         title=app.title,
#         version="1.0.0",
#         description="API for the Best Next Car chatbot backend",
#         routes=app.routes,
#     )
#     app.openapi_schema = openapi_schema
#     return app.openapi_schema

# app.openapi = custom_openapi

# # MongoDB Client (async for endpoints)
# client = AsyncIOMotorClient(MONGO_URI)
# db = client.get_default_database()
# conversations = db.conversations  # Collection for conversation states
# leads = db.leads  # Collection for prequalified leads
# uploads = db.uploads  # Collection for document metadata
# lots_collection = db.lots  # Current and upcoming lots
# sold_collection = db.sold  # Sold archive

# # Sync MongoDB Client for scraping
# sync_client = pymongo.MongoClient(MONGO_URI)
# sync_db = sync_client.get_default_database()
# sync_lots_collection = sync_db.lots
# sync_sold_collection = sync_db.sold

# # Create indexes for fast queries
# sync_lots_collection.create_index([('auction_date', 1), ('source', 1), ('make', 1), ('model', 1), ('location', 1), ('scrape_time', 1)])
# sync_sold_collection.create_index([('auction_date', 1), ('source', 1), ('make', 1), ('model', 1), ('location', 1)])

# # Buyers Premiums (approximate percentages, update as needed)
# house_premiums = {
#     'tradinggarage': 0.12,
#     'carbids': 0.15,
#     'collectingcars': 0.06,
#     'bennettsclassicauctions': 0.125,
#     'burnsandco': 0.15,
#     'lloydsonline': 0.20,
#     'seven82motors': 0.10,
#     'chicaneauctions': 0.12,
#     'doningtonauctions': 0.125
# }

# # Scraping Sources
# SOURCES = [
#     {'url': 'https://www.tradinggarage.com', 'name': 'tradinggarage'},
#     {'url': 'https://collectingcars.com/buy?refinementList%5BlistingStage%5D%5B0%5D=live&refinementList%5BregionCode%5D%5B0%5D=APAC&refinementList%5BcountryCode%5D%5B0%5D=AU', 'name': 'collectingcars'},
#     {'url': 'https://www.bennettsclassicauctions.com.au', 'name': 'bennettsclassicauctions'},
#     {'url': 'https://carbids.com.au/t/unique-and-classic-car-auctions#!?page=1&count=96&filter%5BDisplay%5D=true', 'name': 'carbids'},
#     {'url': 'https://www.lloydsonline.com.au/AuctionLots.aspx?stype=0&stypeid=0&cid=410&smode=0', 'name': 'lloydsonline'},
#     {'url': 'https://www.chicaneauctions.com.au', 'name': 'chicaneauctions'},
#     {'url': 'https://www.seven82motors.com.au', 'name': 'seven82motors'},
#     # Add others if needed
# ]

# # Pydantic Models
# class Message(BaseModel):
#     phone: str  # Used as session identifier
#     body: str

# class LVRInput(BaseModel):
#     vehicle_value: float
#     loan_amount: float

# class ConversationState(BaseModel):
#     phone: str
#     language: str = "English"
#     path: Optional[str] = None  # "preowned" or "new"
#     name: Optional[str] = None
#     budget: Optional[Dict[str, float]] = None  # {"min": float, "max": float}
#     finance_needed: bool = False
#     income_bracket: Optional[str] = None
#     employment_status: Optional[str] = None
#     commitments: Optional[str] = None
#     loan_term: Optional[int] = None
#     down_payment: Optional[float] = None
#     vehicle_interest: Optional[str] = None  # For new path
#     specs: Optional[Dict[str, str]] = None  # Fuel type, etc.
#     selected_vehicle: Optional[Dict] = None
#     last_message_time: datetime = datetime.now(timezone.utc)
#     history: list = []  # List of {"role": "user/system", "content": str}

# # LVR Calculation (as per scope)
# def calculate_lvr(vehicle_value: float, loan_amount: float) -> Dict[str, Any]:
#     if vehicle_value <= 0:
#         return {"lvr_percent": 0, "tier": "invalid"}
#     lvr = (loan_amount / vehicle_value) * 100
#     if lvr <= 100:
#         tier = "preferred"
#     elif lvr <= 130:
#         tier = "acceptable"
#     else:
#         tier = "high_risk"
#     return {"lvr_percent": round(lvr, 1), "tier": tier}

# def get_driver():
#     options = Options()
#     options.add_argument('--headless')  # Modern way to set headless mode
#     options.add_argument('--disable-gpu')  # Often needed for headless
#     options.add_argument('--window-size=1920,1080')  # Avoids some rendering issues
#     if platform.system() == 'Linux':
#         options.add_argument('--no-sandbox')  # Critical for Linux servers
#         options.add_argument('--disable-dev-shm-usage')  # Handles small /dev/shm in containers
#         options.add_argument('--remote-debugging-port=9222')  # For stability in some envs
#     service = Service(ChromeDriverManager().install())
#     return webdriver.Chrome(service=service, options=options)

# def parse_price(price_str):
#     if not price_str or price_str == 'TBA':
#         return None
#     try:
#         if isinstance(price_str, (int, float)):
#             val = float(price_str)
#             return {'low': val, 'high': val}
#         price_str = str(price_str).replace(',', '').replace('$', '').strip()
#         m = re.match(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)', price_str)
#         if m:
#             return {'low': float(m.group(1)), 'high': float(m.group(2))}
#         m = re.match(r'(\d+(?:\.\d+)?)', price_str)
#         if m:
#             val = float(m.group(1))
#             return {'low': val, 'high': val}
#     except:
#         pass
#     return None

# def scrape_site(source):
#     url = source['url']
#     name = source['name']
#     if name == 'bennettsclassicauctions':
#         return scrape_bennetts(url)
#     elif name == 'burnsandco':
#         return scrape_burnsandco(url)
#     elif name == 'carbids':
#         return scrape_carbids(url)
#     elif name == 'tradinggarage':
#         return scrape_tradinggarage(url)
#     elif name == 'collectingcars':
#         return scrape_collectingcars()
#     elif name == 'lloydsonline':
#         return scrape_lloydsonline()
#     elif name == 'chicaneauctions':
#         return scrape_chicane()
#     elif name == 'seven82motors':
#         return scrape_seven82motors()
#     else:
#         # Generic scraper for other sites
#         try:
#             driver = get_driver()
#             driver.get(url)
#             soup = BeautifulSoup(driver.page_source, 'html.parser')
#             driver.quit()
#             listings = []
#             item_class = 'auction-item' # Adjust per site as needed
#             for item in soup.find_all('div', class_=item_class):
#                 lot = parse_lot(item, url)
#                 if lot and is_classic(lot):
#                     lot['source'] = name
#                     listings.append(lot)
#             return listings
#         except Exception as e:
#             print(f"Error scraping {url}: {e}")
#             return []

# def scrape_tradinggarage(base_url="https://www.tradinggarage.com"):
#     listings = []
#     session = requests.Session()
#     session.headers.update({
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
#         'Accept': 'application/json',
#         'Referer': 'https://www.tradinggarage.com/',
#     })
#     endpoints = {
#         'live': 'https://portal.tradinggarage.com/api/v1/auctions?status=live',
#         'coming_soon': 'https://portal.tradinggarage.com/api/v1/auctions?status=coming_soon'
#     }
#     for status, api_url in endpoints.items():
#         try:
#             r = session.get(api_url, timeout=12)
#             if r.status_code != 200:
#                 continue
#             data = r.json()
#             auctions = data.get('data', []) or data.get('auctions', []) or []
#             for auction in auctions:
#                 if auction.get('object_type') != 'vehicle':
#                     continue
#                 title = auction.get('title', 'Unknown Car')
#                 year_str = ''
#                 make = ''
#                 model = ''
#                 m = re.search(r'(\d{4})\s*([a-zA-Z0-9\-() ]+)\s+(.+)', title)
#                 if m:
#                     year_str = m.group(1)
#                     make = m.group(2).strip()
#                     model = m.group(3).strip()
#                 try:
#                     year = int(year_str)
#                 except:
#                     year = 0
#                 price_str = auction.get('last_bid', '0')
#                 auction_date = None
#                 try:
#                     auction_date = parse(auction['auction_end_at'])
#                 except:
#                     pass
#                 images = [auction.get('title_image', '')]
#                 url = f"https://www.tradinggarage.com/products/{auction.get('slug', '')}"
#                 reserve = 'No' if auction.get('no_reserve', False) else 'Yes'
#                 location = 'Online / Melbourne'
#                 description = ''
#                 odometer = ''
#                 lot = {
#                     'source': 'tradinggarage',
#                     'status': auction['status']['name'],
#                     'auction_id': auction['id'],
#                     'title': title,
#                     'year': year,
#                     'make': make,
#                     'model': model,
#                     'odometer': odometer,
#                     'price_range': parse_price(price_str),
#                     'auction_date': auction_date,
#                     'location': location,
#                     'images': images,
#                     'url': url,
#                     'description': description,
#                     'reserve': reserve,
#                     'scrape_time': datetime.now(timezone.utc)
#                 }
#                 if is_classic(lot):
#                     listings.append(lot)
#         except Exception as e:
#             pass
#     return listings

# def scrape_collectingcars():
#     listings = []
#     api_url = "https://dora.production.collecting.com/multi_search"
#     headers = {
#         'x-typesense-api-key': 'aKIufK0SfYHMRp9mUBkZPR7pksehPBZq',
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
#         'Accept': 'application/json',
#         'Content-Type': 'application/json',
#         'Referer': 'https://collectingcars.com/',
#     }
#     base_payload = {
#         "searches": [
#             {
#                 "query_by": "title,productMake,vehicleMake,productYear,tags,lotType,driveSide,location,collectionId,modelId",
#                 "query_by_weights": "9,8,7,6,5,4,3,2,1,0",
#                 "text_match_type": "sum_score",
#                 "sort_by": "rank:asc",
#                 "highlight_full_fields": "*",
#                 "facet_by": "lotType, regionCode, countryCode, saleFormat, noReserve, isBoosted, productMake, vendorType, driveSide, listingStage, tags",
#                 "max_facet_values": 999,
#                 "facet_counts": True,
#                 "facet_stats": True,
#                 "facet_distribution": True,
#                 "facet_return_parent": True,
#                 "collection": "production_cars",
#                 "q": "*",
#                 "filter_by": "listingStage:=[`live`] && countryCode:=[`AU`] && regionCode:=[`APAC`]",
#                 "page": 1,
#                 "per_page": 50
#             }
#         ]
#     }
#     page = 1
#     while True:
#         base_payload["searches"][0]["page"] = page
#         try:
#             response = requests.post(api_url, headers=headers, json=base_payload, timeout=15)
#             if response.status_code != 200:
#                 break
#             data = response.json()
#             if "results" not in data or not data["results"]:
#                 break
#             result = data["results"][0]
#             hits = result.get("hits", [])
#             if not hits:
#                 break
#             for hit in hits:
#                 doc = hit.get("document", {})
#                 if doc.get('lotType') != 'car':
#                     continue
#                 title = doc.get('title', 'Unknown Car')
#                 year_str = doc.get('productYear', '')
#                 try:
#                     year = int(year_str)
#                 except:
#                     year = 0
#                 make = doc.get('productMake', '') or doc.get('vehicleMake', '')
#                 model = doc.get('modelName', '') + ' ' + doc.get('variantName', '').strip()
#                 price_str = doc.get('currentBid', 0)
#                 auction_date = None
#                 try:
#                     auction_date = parse(doc['dtStageEndsUTC'])
#                 except:
#                     pass
#                 images = [doc.get('mainImageUrl', '')]
#                 url = f"https://collectingcars.com/for-sale/{doc.get('slug', '')}"
#                 reserve = 'No' if doc.get('noReserve') == "true" else 'Yes'
#                 location = doc.get('location', 'Australia')
#                 description = '' # No description in data
#                 odometer = doc['features'].get('mileage', '')
#                 transmission = doc['features'].get('transmission', extract_transmission(title))
#                 body_style = extract_body_style(title)
#                 fuel_type = doc['features'].get('fuelType', '')
#                 lot = {
#                     'source': 'collectingcars',
#                     'status': doc['listingStage'],
#                     'auction_id': doc['auctionId'],
#                     'title': title,
#                     'year': year,
#                     'make': make,
#                     'model': model,
#                     'odometer': odometer,
#                     'price_range': parse_price(price_str),
#                     'auction_date': auction_date,
#                     'location': location,
#                     'images': images,
#                     'url': url,
#                     'description': description,
#                     'reserve': reserve,
#                     'body_style': body_style,
#                     'transmission': transmission,
#                     'fuel_type': fuel_type,
#                     'scrape_time': datetime.now(timezone.utc)
#                 }
#                 if is_classic(lot):
#                     listings.append(lot)
#             page += 1
#             time.sleep(1.2)
#         except Exception as e:
#             break
#     return listings

# def scrape_chicane(url='https://www.chicaneauctions.com.au/february-2026-classic-car-auction/'):
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
#                       '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
#     }
#     try:
#         resp = requests.get(url, headers=headers, timeout=20)
#         resp.raise_for_status()
#     except Exception as e:
#         print(f"Error fetching Chicane page: {e}")
#         return []
#     soup = BeautifulSoup(resp.text, 'html.parser')
#     listings = []
#     base_url = 'https://www.chicaneauctions.com.au'
#     for item in soup.select('.promo_box'):
#         try:
#             button = item.select_one('.desc_wrapper .button')
#             link = button if button else item.select_one('.desc_wrapper a')
#             if not link:
#                 continue
#             relative_href = link.get('href', '').strip()
#             if not relative_href:
#                 continue
#             full_url = relative_href if relative_href.startswith('http') else base_url + relative_href
#             if '/sell/' in full_url.lower():
#                 continue
#             title_tag = item.select_one('.desc_wrapper .title')
#             title = title_tag.get_text(strip=True) if title_tag else ''
#             if not title:
#                 continue
#             title_upper = title.upper()
#             if '- OPEN POSITION -' in title_upper or 'STAY TUNED' in title_upper:
#                 continue
#             img_tag = item.select_one('.photo_wrapper img')
#             img_src = None
#             if img_tag:
#                 img_src = img_tag.get('data-src') or img_tag.get('src')
#                 if img_src and img_src.startswith('//'):
#                     img_src = 'https:' + img_src
#             if not img_src or 'upcoming-classic-car-auction-house.png' in img_src:
#                 continue
#             images = [img_src] if img_src else []
#             lot_num = None
#             m = re.search(r'(?:lot[-_\s]*)(\d+)', full_url, re.IGNORECASE)
#             if m:
#                 lot_num = m.group(1)
#             if not lot_num:
#                 m = re.search(r'(?:lot|Lot|LOT)\s*(\d+)', title, re.IGNORECASE)
#                 if m:
#                     lot_num = m.group(1)
#             year = None
#             make = ''
#             model = ''
#             m = re.match(r'^(\d{4})\s+([A-Za-z0-9\-]+(?:\s+[A-Za-z0-9\-]+)*?)(?:\s+(.+?))?(?:\s*-|$)', title.strip())
#             if m:
#                 try:
#                     year = int(m.group(1))
#                 except:
#                     pass
#                 make = (m.group(2) or '').strip()
#                 model = (m.group(3) or '').strip()
#             if not year:
#                 ym = re.search(r'\b(19\d{2}|20\d{2})\b', title)
#                 if ym:
#                     year = int(ym.group(1))
#             location = {
#                 'city': 'Melbourne',
#                 'state': 'VIC',
#                 'country': 'Australia'
#             }
#             lot = {
#                 'source': 'chicaneauctions',
#                 'auction_id': lot_num or title.lower().replace(' ', '-').replace('--', '-'),
#                 'title': title,
#                 'url': full_url,
#                 'year': year,
#                 'make': make,
#                 'model': model,
#                 'vehicle': {
#                     'year': year,
#                     'make': make,
#                     'model': model,
#                 },
#                 'price': {
#                     'current': None,  # not shown on pre-catalogue
#                     'reserve': 'Unknown',
#                 },
#                 'auction_end': None,  # not shown yet
#                 'location': location,
#                 'images': images,
#                 'condition': {
#                     'comment': title,  # can be improved later from detail page
#                 },
#                 'status': 'upcoming',
#                 'scrape_time': datetime.now(timezone.utc).isoformat(),
#             }
#             if is_classic(lot):
#                 listings.append(lot)
#         except Exception as e:
#             print(f"Error parsing one Chicane promo_box: {e}")
#             continue
#     return listings

# def scrape_lloydsonline(url='https://www.lloydsonline.com.au/AuctionLots.aspx?stype=0&stypeid=0&cid=410&smode=0'):
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
#     }
#     try:
#         resp = requests.get(url, headers=headers, timeout=20)
#         if resp.status_code != 200:
#             print(f"Lloyds returned {resp.status_code}")
#             return []
#         html_content = resp.text
#     except Exception as e:
#         print(f"Error fetching Lloyds: {e}")
#         return []
#     soup = BeautifulSoup(html_content, 'html.parser')
#     listings = []
#     base_url = 'https://www.lloydsonline.com.au'
#     for item in soup.select('.gallery_item.lot_list_item'):
#         try:
#             link = item.select_one('a[href^="LotDetails.aspx"]')
#             relative_href = link.get('href') if link else None
#             full_url = None
#             if relative_href:
#                 full_url = base_url + '/' + relative_href.lstrip('/')
#             lot_num_elem = item.select_one('.lot_num')
#             lot_num = lot_num_elem.text.strip() if lot_num_elem else None
#             img_tag = item.select_one('.lot_img img')
#             img_src = None
#             if img_tag and img_tag.has_attr('src'):
#                 img_src = img_tag['src'].strip()
#                 if img_src.startswith('//'):
#                     img_src = 'https:' + img_src
#             images = [img_src] if img_src else []
#             desc_elem = item.select_one('.lot_desc')
#             title = desc_elem.get_text(strip=True) if desc_elem else ''
#             year = None
#             make = ''
#             model = ''
#             m = re.match(r'^(\d{4})\s+(.+?)\s+(.+?)(?:\s+|$)', title)
#             if m:
#                 try:
#                     year = int(m.group(1))
#                 except ValueError:
#                     pass
#                 make = m.group(2).strip()
#                 model = m.group(3).strip()
#             bid_tag = item.select_one('.lot_cur_bid span, .lot_bidding span')
#             current_bid_str = bid_tag.get_text(strip=True) if bid_tag else '0'
#             current_bid = None
#             try:
#                 current_bid = float(re.sub(r'[^\d.]', '', current_bid_str))
#             except (ValueError, TypeError):
#                 pass
#             time_rem_tag = item.select_one('[data-seconds_rem]')
#             seconds_rem = 0
#             if time_rem_tag and time_rem_tag.has_attr('data-seconds_rem'):
#                 try:
#                     seconds_rem = int(time_rem_tag['data-seconds_rem'])
#                 except ValueError:
#                     pass
#             auction_end = datetime.now(timezone.utc) + timedelta(seconds=seconds_rem) if seconds_rem > 0 else None
#             location_img = item.select_one('.auctioneer-location img')
#             state_src = location_img.get('src', '').split('/')[-1] if location_img else ''
#             state_map = {
#                 's_1.png': 'ACT', 's_2.png': 'NT', 's_3.png': 'NSW',
#                 's_4.png': 'QLD', 's_5.png': 'SA', 's_6.png': 'TAS',
#                 's_7.png': 'WA', 's_8.png': 'VIC',
#             }
#             state = state_map.get(state_src, '')
#             location = {'state': state}
#             unreserved = item.select_one('.sash.ribbon-blue')
#             reserve = 'No' if unreserved and 'UNRESERVED' in (unreserved.get_text(strip=True) or '').upper() else 'Yes'
#             vehicle = {
#                 'year': year,
#                 'make': make,
#                 'model': model,
#             }
#             price = {
#                 'current': current_bid,
#             }
#             condition = {
#                 'comment': title,
#             }
#             lot = {
#                 'source': 'lloydsonline',
#                 'auction_id': lot_num,  # or use data-lot_id if available
#                 'title': title,
#                 'url': full_url,
#                 'year': year,
#                 'make': make,
#                 'model': model,
#                 'vehicle': vehicle,
#                 'price': price,
#                 'auction_end': auction_end,
#                 'location': location,
#                 'images': images,
#                 'condition': condition,
#                 'reserve': reserve,
#                 'status': 'live' if seconds_rem > 0 else 'ended',
#                 'scrape_time': datetime.now(timezone.utc),
#             }
#             if is_classic(lot):
#                 listings.append(lot)
#         except Exception as e:
#             print(f"Error parsing Lloyds lot: {str(e)}")
#     return listings

# def scrape_carbids_api():
#     listings = []
#     session = requests.Session()
#     session.headers.update({
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
#         'Accept': 'application/json, text/plain, */*',
#         'X-Requested-With': 'XMLHttpRequest',
#         'Referer': 'https://carbids.com.au/',
#         'Origin': 'https://carbids.com.au',
#     })
#     try:
#         home = session.get("https://carbids.com.au/t/unique-and-classic-car-auctions")
#         soup = BeautifulSoup(home.text, 'html.parser')
#         token_input = soup.find('input', {'name': '__RequestVerificationToken'})
#         if token_input and token_input.get('value'):
#             session.headers['__RequestVerificationToken'] = token_input['value']
#     except:
#         pass
#     page = 0
#     while True:
#         payload = {
#             "top": 96,
#             "skip": page * 96,
#             "sort": {"aucClose": "asc"},
#             "tagName": "Unique and Classic Car Auctions",
#             "filter": {"Display": True}
#         }
#         try:
#             resp = session.post(
#                 "https://carbids.com.au/Search/Tags",
#                 json=payload,
#                 timeout=20
#             )
#             if resp.status_code != 200:
#                 print(f"Carbids API returned {resp.status_code}")
#                 break
#             data = resp.json()
#             auctions = data.get("auctions", [])
#             if not auctions:
#                 break
#             for auc in auctions:
#                 title = auc.get("aucTitle", "").strip()
#                 title_text = auc.get("aucTitleText", title).strip()
#                 short_title = auc.get("aucTitleShortText", title).strip()
#                 year = None
#                 make = ""
#                 model = ""
#                 m = re.match(r'^(\d{1,2}/)?(\d{4})\s+(.+?)\s+(.+?)(?:\s+|$)', title_text)
#                 if m:
#                     year_str = m.group(2)
#                     make = m.group(3).strip()
#                     model = m.group(4).strip()
#                     try:
#                         year = int(year_str)
#                     except:
#                         year = None
#                 if not year and auc.get("aucYear"):
#                     try:
#                         year = int(auc["aucYear"])
#                     except:
#                         pass
#                 make = auc.get("aucMake", make).strip()
#                 model = auc.get("aucModel", model).strip()
#                 current_bid = auc.get("aucCurrentBid", 0.0)
#                 starting_bid = auc.get("aucStartingBid", 1.0)
#                 price_info = {
#                     "current": float(current_bid) if current_bid else None,
#                     "starting": float(starting_bid) if starting_bid else None,
#                     "increment": auc.get("aucBidIncrement", 0.0),
#                     "buyers_premium_text": auc.get("aucBPText", ""),
#                     "gst_note": auc.get("isGstApplicableWording", "")
#                 }
#                 end_date_str = auc.get("aucCloseUtc")
#                 auction_end = None
#                 if end_date_str:
#                     try:
#                         auction_end = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
#                     except:
#                         try:
#                             auction_end = parse(end_date_str)
#                         except:
#                             pass
#                 location = {
#                     "city": auc.get("aucCity", ""),
#                     "state": auc.get("aucState", ""),
#                     "address": auc.get("aucAddressLocation", ""),
#                     "pickup": auc.get("aucPickupAvailable", False),
#                     "freight": auc.get("aucFreightAvailable", False),
#                     "freight_limits": auc.get("aucItemFreightLimits", "")
#                 }
#                 vehicle = {
#                     "year": year,
#                     "make": make,
#                     "model": model,
#                     "odometer_km": auc.get("aucOdometerNumber"),
#                     "odometer_display": auc.get("aucOdometer", ""),
#                     "transmission": auc.get("aucTransmission"),
#                     "fuel_type": auc.get("aucFuelType"),
#                     "engine_capacity": auc.get("aucCapacity"),
#                     "cylinders": auc.get("aucCylinder"),
#                     "drivetrain": auc.get("aucDrv"),
#                 }
#                 images = []
#                 base = auc.get("aucCarsThumbnailUrl", auc.get("aucThumbnailUrl", ""))
#                 if base:
#                     images.append(base)
#                 for size in ["small", "medium", "large"]:
#                     key = f"aucCars{size.capitalize()}ThumbnailUrl"
#                     if auc.get(key):
#                         images.append(auc[key])
#                 medium_list = auc.get("aucMediumThumbnailUrlList", [])
#                 images.extend([url for url in medium_list if url])
#                 condition = {
#                     "body": auc.get("aucBodyCondition"),
#                     "paint": auc.get("aucPaintCondition"),
#                     "features_text": auc.get("aucFeaturesText"),
#                     "key_facts": auc.get("aucKeyFactsText"),
#                     "comment": auc.get("aucComment"),
#                     "service_history": auc.get("aucServiceHistory"),
#                 }
#                 lot = {
#                     "source": "carbids",
#                     "auction_id": auc.get("aucID"),
#                     "reference_number": auc.get("aucReferenceNo"),
#                     "title": title_text,
#                     "short_title": short_title,
#                     "url": "https://carbids.com.au/" + auc.get("AucDetailsUrlLink", "").lstrip("/"),
#                     "year": year,
#                     "make": make,
#                     "model": model,
#                     "vehicle": vehicle,
#                     "price": price_info,
#                     "auction_end": auction_end,
#                     "location": location,
#                     "images": images[:8], # limit to 8 for storage
#                     "condition": condition,
#                     "reserve": "Yes", # currently no reserve field → assume Yes
#                     "status": "live", # we only get live auctions here
#                     "scrape_time": datetime.now(timezone.utc),
#                 }
#                 if is_classic(lot):
#                     listings.append(lot)
#             page += 1
#             time.sleep(1.3) # polite delay
#         except Exception as e:
#             print("Error in carbids API loop:", str(e))
#             break
#     return listings

# def scrape_carbids(base_url):
#     listings_api = scrape_carbids_api()
#     combined = listings_api
#     seen_urls = set()
#     unique = []
#     for lot in combined:
#         u = lot.get("url")
#         if u and u not in seen_urls:
#             seen_urls.add(u)
#             unique.append(lot)
#     return unique

# def scrape_bennetts(base_url="https://www.bennettsclassicauctions.com.au"):
#     pages = [base_url, base_url + '/off-site.php']
#     all_listings = []
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
#     }
#     for page_url in pages:
#         try:
#             resp = requests.get(page_url, headers=headers, timeout=20)
#             resp.raise_for_status()
#             soup = BeautifulSoup(resp.text, 'html.parser')
#             sitename = soup.find('div', id='sitename')
#             h3 = sitename.find('h3') if sitename else None
#             auction_text = h3.text.strip() if h3 else ''
#             date_match = re.search(r'(\d{1,2}[ST|ND|RD|TH]{0,2} \w+ \d{4})', auction_text.upper())
#             time_match = re.search(r'@ (\d{1,2}[AP]M)', auction_text.upper())
#             auction_date_str = ''
#             if date_match:
#                 date_str = re.sub(r'([ST|ND|RD|TH])', '', date_match.group(1))
#                 auction_date_str += date_str
#             if time_match:
#                 auction_date_str += ' ' + time_match.group(1)
#             auction_date = None
#             try:
#                 auction_date = parse(auction_date_str)
#             except:
#                 pass
#             sections = soup.find_all('div', class_='clear')
#             for section in sections:
#                 column = section.find('div', class_='column column-600 column-left')
#                 if column:
#                     h3_cat = column.find('h3')
#                     category = h3_cat.text.strip() if h3_cat else ''
#                     table = column.find('table')
#                     if table:
#                         tbody = table.find('tbody')
#                         trs = tbody.find_all('tr') if tbody else table.find_all('tr')
#                         for tr in trs[1:]:  # Skip header
#                             tds = tr.find_all('td')
#                             if len(tds) >= 7:  # Ensure enough columns
#                                 photo_td = tds[0]
#                                 a = photo_td.find('a')
#                                 detail_url = base_url + '/' + a['href'].lstrip('/') if a else ''
#                                 img = photo_td.find('img')
#                                 image_src = base_url + '/' + img['src'].lstrip('/') if img and img['src'].startswith('images') else (img['src'] if img else '')
#                                 make = tds[1].text.strip()
#                                 stock_model = tds[2].text.strip()
#                                 parts = stock_model.split('/')
#                                 stock_ref = parts[0].strip() if parts else ''
#                                 model = parts[1].strip() if len(parts) > 1 else stock_model
#                                 year_str = tds[3].text.strip()
#                                 try:
#                                     year = int(year_str)
#                                 except:
#                                     year = 0
#                                 options = tds[4].text.strip()
#                                 location_td = tds[5]
#                                 location = location_td.text.strip().replace('\n', '').replace('br /', '')
#                                 lot = {
#                                     'source': 'bennettsclassicauctions',
#                                     'make': make,
#                                     'model': model,
#                                     'year': year,
#                                     'price_range': None,
#                                     'auction_date': auction_date,
#                                     'location': location,
#                                     'images': [image_src] if image_src else [],
#                                     'url': detail_url,
#                                     'description': options,
#                                     'reserve': 'Yes',
#                                     'body_style': extract_body_style(options),
#                                     'transmission': extract_transmission(options),
#                                     'scrape_time': datetime.now(timezone.utc)
#                                 }
#                                 if is_classic(lot):
#                                     all_listings.append(lot)
#         except Exception as e:
#             print(f"Error scraping Bennetts ({page_url}): {str(e)}")
#     return all_listings

# def scrape_burnsandco(base_url="https://burnsandcoauctions.com.au"):
#     pages = [base_url + '/current-auctions/', base_url + '/upcoming-auctions/']
#     all_listings = []
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
#     }
#     for page_url in pages:
#         try:
#             resp = requests.get(page_url, headers=headers, timeout=20)
#             resp.raise_for_status()
#             soup = BeautifulSoup(resp.text, 'html.parser')
#             articles = soup.find_all('article', class_='regular masonry-blog-item')
#             for article in articles:
#                 img_link = article.find('a', class_='img-link')
#                 detail_url = img_link['href'] if img_link else ''
#                 img = img_link.find('img') if img_link else None
#                 image_src = img['src'] if img else ''
#                 meta_category = article.find('span', class_='meta-category')
#                 category = meta_category.text.strip() if meta_category else ''
#                 date_item = article.find('span', class_='date-item')
#                 auction_date_str = date_item.text.strip() if date_item else ''
#                 auction_date = None
#                 try:
#                     auction_date = parse(auction_date_str)
#                 except:
#                     pass
#                 title_a = article.find('h3', class_='title').find('a') if article.find('h3', class_='title') else None
#                 title = title_a.text.strip() if title_a else ''
#                 excerpt = article.find('div', class_='excerpt').text.strip() if article.find('div', class_='excerpt') else ''
#                 place = article.find('p', class_='place').text.strip() if article.find('p', class_='place') else ''
#                 bid_links = article.find_all('p', class_='registration_bidding_link')
#                 for bid_p in bid_links:
#                     bid_a = bid_p.find('a')
#                     bid_url = bid_a['href'] if bid_a else ''
#                     catalogue_lots = scrape_catalogue(bid_url)
#                     for cat_lot in catalogue_lots:
#                         cat_lot['auction_date'] = auction_date or cat_lot.get('auction_date')
#                         cat_lot['location'] = place or cat_lot.get('location')
#                         cat_lot['source'] = 'burnsandco'
#                         all_listings.append(cat_lot)
#         except Exception as e:
#             print(f"Error scraping Burns and Co ({page_url}): {str(e)}")
#     return all_listings

# def scrape_seven82motors():
#     listings = []
#     auction_slug = "march-29th-2026"
#     api_url = f"https://seven82-json-sb.manage.auction/listings/auctions/{auction_slug}?amt=100"
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
#                       '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
#         'Accept': 'application/json',
#         'Referer': 'https://www.seven82motors.com.au/',
#     }
#     try:
#         resp = requests.get(api_url, headers=headers, timeout=20)
#         resp.raise_for_status()
#         data = resp.json()
#         auction_title = data.get("heading", "Unknown Auction Date")
#         auction_date = None
#         date_str_candidates = [
#             auction_title,
#             data.get("breadcrumbs", [{}])[0].get("title", ""),
#             f"{auction_title} 2026",
#             auction_slug.replace("-", " ").title()
#         ]
#         for candidate in date_str_candidates:
#             if not candidate:
#                 continue
#             try:
#                 auction_date = parse(candidate, fuzzy=True, dayfirst=False)
#                 if auction_date.year >= 2025:
#                     break
#             except:
#                 continue
#         if not auction_date:
#             auction_date = datetime.now(timezone.utc) + timedelta(days=60)
#         items = data.get("items", [])
#         for item in items:
#             if item.get("dummy_lot", 0) == 1:
#                 continue
#             title = (item.get("title") or "").strip()
#             if not title:
#                 continue
#             if any(phrase in title.upper() for phrase in [
#                 "SELL YOUR CAR", "CONSIGN", "REGISTER AND BID", "LEARN HOW TO"
#             ]):
#                 continue
#             year = None
#             make = ""
#             model = ""
#             clean_title = re.sub(
#                 r'^(NO RESERVE!?\s*|RARE\s*|FULLY RESTORED\s*|CUSTOM\s*)',
#                 '', title, flags=re.IGNORECASE
#             ).strip()
#             m = re.match(r'^(\d{4})\s+(.+?)(?:\s+(.+?))?(?:\s+|$)', clean_title)
#             if m:
#                 try:
#                     year = int(m.group(1))
#                 except:
#                     pass
#                 make_model_part = (m.group(2) or "").strip()
#                 extra = (m.group(3) or "").strip()
#                 parts = make_model_part.split(maxsplit=1)
#                 if parts:
#                     make = parts[0].strip()
#                     if len(parts) > 1:
#                         model = parts[1].strip()
#                     model = f"{model} {extra}".strip()
#             reserve = "No" if "NO RESERVE" in title.upper() else "Yes"
#             images = []
#             featured = item.get("media_featured", [])
#             if isinstance(featured, list):
#                 for img_obj in featured:
#                     if isinstance(img_obj, dict):
#                         src = img_obj.get("src")
#                         if src and "catalog/" in src:
#                             clean_src = src.lstrip('/')
#                             full_url = f"https://seven82motors.mymedia.delivery/{clean_src}"
#                             if full_url not in images:
#                                 images.append(full_url)
#             main_img = item.get("image")
#             if main_img and "catalog/" in main_img:
#                 clean_main = main_img.lstrip('/')
#                 full_main = f"https://seven82motors.mymedia.delivery/{clean_main}"
#                 if full_main not in images:
#                     images.insert(0, full_main)
#             seen = set()
#             clean_images = []
#             for url in images:
#                 if url and url not in seen:
#                     seen.add(url)
#                     if not any(x in url.lower() for x in ["thumb", "small", "placeholder", "watermark"]):
#                         clean_images.append(url)
#             images = clean_images[:12]
#             is_coming_soon = False
#             coming_soon_data = item.get("coming_soon", [])
#             if isinstance(coming_soon_data, list):
#                 for entry in coming_soon_data:
#                     if isinstance(entry, dict):
#                         if entry.get("settings", {}).get("coming_soon") in (True, "1", 1, "true"):
#                             is_coming_soon = True
#                             break
#             lot_path = item.get('path', '').lstrip('/')
#             lot_url = f"https://www.seven82motors.com.au/lot/{lot_path}" if lot_path else ""
#             lot = {
#                 'source': 'seven82motors',
#                 'status': 'upcoming',
#                 'auction_id': item.get("id"),
#                 'lot_number': item.get("number"),
#                 'title': title,
#                 'year': year,
#                 'make': make,
#                 'model': model,
#                 'odometer': None,  # detail page only
#                 'price_range': None,  # not in list view
#                 'auction_date': auction_date,
#                 'location': "Brisbane, QLD (Online)",
#                 'images': images,
#                 'url': lot_url,
#                 'description': (item.get("description_short") or "").strip(),
#                 'reserve': reserve,
#                 'body_style': None,
#                 'transmission': None,
#                 'fuel_type': None,
#                 'scrape_time': datetime.now(timezone.utc),
#                 'coming_soon': is_coming_soon,
#                 'buyers_premium_pct': 8.8,
#                 'auction_title': auction_title,
#                 'raw_filters': item.get("filters", {}),
#             }
#             if is_classic(lot):
#                 listings.append(lot)
#     except Exception as e:
#         print(f"[seven82motors] Error scraping {auction_slug}: {e}")
#     return listings

# def scrape_catalogue(catalogue_url):
#     listings = []
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
#     }
#     try:
#         resp = requests.get(catalogue_url, headers=headers, timeout=20)
#         resp.raise_for_status()
#         soup = BeautifulSoup(resp.text, 'html.parser')
#         table = soup.find('table')  # Or find('table', class_='catalogue-table') if specific class
#         if table:
#             trs = table.find_all('tr')
#             for tr in trs[1:]:  # Skip header row
#                 tds = tr.find_all('td')
#                 if len(tds) < 4:
#                     continue
#                 lot_number = tds[0].text.strip()
#                 desc_td = tds[1]
#                 desc = desc_td.text.strip()
#                 match = re.match(r'(\d{4})? ?(.*?) (.*)', desc)
#                 year_str = match.group(1) if match and match.group(1) else ''
#                 try:
#                     year = int(year_str)
#                 except:
#                     year = 0
#                 make = match.group(2) if match else ''
#                 model = match.group(3) if match else desc
#                 images = [urljoin(catalogue_url, img['src']) for img in tr.find_all('img') if 'src' in img.attrs]
#                 detail_a = desc_td.find('a')
#                 detail_url = urljoin(catalogue_url, detail_a['href']) if detail_a else ''
#                 current_bid = tds[2].text.strip()
#                 lot = {
#                     'lot_number': lot_number,
#                     'make': make,
#                     'model': model,
#                     'year': year,
#                     'price_range': parse_price(current_bid),
#                     'auction_date': None,
#                     'location': None,
#                     'images': images,
#                     'url': detail_url,
#                     'description': desc,
#                     'reserve': 'Yes',
#                     'body_style': extract_body_style(desc),
#                     'transmission': extract_transmission(desc),
#                     'scrape_time': datetime.now(timezone.utc)
#                 }
#                 if is_classic(lot):
#                     listings.append(lot)
#     except Exception as e:
#         print(f"Error scraping catalogue ({catalogue_url}): {str(e)}")
#     return listings

# def parse_lot(item, url):
#     try:
#         description = item.find('p', class_='desc') or item.find('div', class_='description')
#         description_text = description.text.strip() if description else ''
#         year_elem = item.find('span', class_='year') or item.find('h3')
#         year_str = year_elem.text.strip() if year_elem else '0'
#         try:
#             year = int(year_str)
#         except:
#             year = 0
#         make_elem = item.find('span', class_='make') or item.find('h2')
#         model_elem = item.find('span', class_='model')
#         price_elem = item.find('span', class_='estimate') or item.find('div', class_='price')
#         price_str = price_elem.text.strip() if price_elem else None
#         date_elem = item.find('span', class_='date')
#         location_elem = item.find('span', class_='location')
#         link_elem = item.find('a', class_='lot-link') or item.find('a')
#         lot = {
#             'make': make_elem.text.strip() if make_elem else None,
#             'model': model_elem.text.strip() if model_elem else None,
#             'year': year,
#             'price_range': parse_price(price_str),
#             'auction_date': parse_date(date_elem.text.strip()) if date_elem else None,
#             'location': location_elem.text.strip() if location_elem else 'Online',
#             'images': [img['src'] for img in item.find_all('img', class_='thumbnail')][:6],
#             'url': link_elem['href'] if link_elem else url,
#             'description': description_text,
#             'reserve': 'No' if 'no reserve' in description_text.lower() else 'Yes',
#             'body_style': extract_body_style(description_text),
#             'transmission': extract_transmission(description_text),
#             'scrape_time': datetime.now(timezone.utc)
#         }
#         return lot
#     except:
#         return None

# def parse_date(date_str):
#     try:
#         return parse(date_str)
#     except:
#         return None

# def extract_body_style(desc):
#     lower_desc = desc.lower()
#     styles = ['coupe', 'convertible', 'sedan', 'wagon', 'ute', 'truck']
#     for style in styles:
#         if style in lower_desc:
#             return style.capitalize()
#     return None

# def extract_transmission(desc):
#     lower_desc = desc.lower()
#     if 'manual' in lower_desc:
#         return 'Manual'
#     if 'auto' in lower_desc or 'automatic' in lower_desc:
#         return 'Automatic'
#     return None

# def is_classic(lot):
#     year = lot.get('year')
#     if year is None or not isinstance(year, (int, float)):
#         text = (lot.get('title', '') + ' ' + lot.get('description', '')).lower()
#         has_classic_hint = any(word in text for word in [
#             'classic', 'muscle', 'vintage', 'hot rod', 'restored', 'collector',
#             'holden', 'falcon gt', 'monaro', 'charger', 'mustang', 'corvette'
#         ])
#         return has_classic_hint
#     if year < 2005:
#         return True
#     text = (lot.get('title', '') + ' ' + lot.get('description', '')).lower()
#     modern_classic_keywords = [
#         'hellcat', 'demon', 'supercharged', 'stroker', 'r8', 'gts-r', 'boss 302',
#         'shelby', 'a9x', 'fpv', 'gtr', 'torana', 'monaro'
#     ]
#     return any(kw in text for kw in modern_classic_keywords)

# def normalize_auction_date(ad):
#     if not ad:
#         return None
#     if isinstance(ad, datetime):
#         return ad
#     if isinstance(ad, str):
#         try:
#             return parse(ad)
#         except:
#             return None
#     try:
#         return parse(str(ad))
#     except:
#         return None

# # Scrape all and store in DB (sync version)
# def scrape_all():
#     all_lots = []
#     scrape_start = datetime.now(timezone.utc)
#     for source in SOURCES:
#         lots = scrape_site(source)
#         all_lots.extend(lots)
    
#     for lot in all_lots:
#         lot['scrape_time'] = datetime.now(timezone.utc)
#         lot['auction_date'] = normalize_auction_date(lot.get('auction_date'))
#         if not lot.get('url'):
#             lot['url'] = f"{lot.get('source','unknown')}/{uuid.uuid4()}"
#         sync_lots_collection.update_one(
#             {'url': lot['url']},
#             {'$set': lot, '$setOnInsert': {'first_scraped': scrape_start}},
#             upsert=True
#         )
    
#     now = datetime.now(timezone.utc)
#     ended = list(sync_lots_collection.find({'auction_date': {'$lt': now}}))
#     for end in ended:
#         house = end['source']
#         prem = house_premiums.get(house, 0.15)
#         hammer = end.get('price_range', {}).get('high', 0)
#         total = hammer * (1 + prem)
#         sold_doc = dict(end)
#         sold_doc['hammer_price'] = hammer
#         sold_doc['buyers_premium'] = prem * 100
#         sold_doc['total_price'] = total
#         sync_sold_collection.insert_one(sold_doc)
#         sync_lots_collection.delete_one({'_id': end['_id']})
    
#     two_years_ago = now - timedelta(days=730)
#     sync_sold_collection.delete_many({'auction_date': {'$lt': two_years_ago}})

# # Scheduler for scraping
# scheduler = BackgroundScheduler()
# scheduler.add_job(scrape_all, 'interval', hours=1)
# scheduler.start()



# async def fetch_vehicles(path: str, criteria: Dict, page: int, page_size: int):
#     if path != "preowned":
#         return [], 0

#     query = {}

#     if "min_price" in criteria:
#         query["price_range.low"] = {"$gte": criteria["min_price"]}

#     if "max_price" in criteria:
#         query["price_range.high"] = {"$lte": criteria["max_price"]}

#     if "interest" in criteria:
#         interest = criteria["interest"]
#         query["$or"] = [
#             {"make": {"$regex": interest, "$options": "i"}},
#             {"model": {"$regex": interest, "$options": "i"}},
#             {"title": {"$regex": interest, "$options": "i"}},
#             {"description": {"$regex": interest, "$options": "i"}}
#         ]

#     # Pagination logic
#     skip = (page - 1) * page_size

#     total = await lots_collection.count_documents(query)

#     cursor = (
#         lots_collection
#         .find(query)
#         .skip(skip)
#         .limit(page_size)
#     )

#     vehicles = await cursor.to_list(length=page_size)

#     return [dict(v, _id=str(v["_id"])) for v in vehicles], total
# # xAI API Integration for Conversational AI
# async def generate_ai_response(state: ConversationState, user_message: str) -> str:
#     system_prompt = f"""
#     You are an AI car finder for Australian users. Follow the project scope strictly.
#     Handle onboarding, language selection, preowned/new paths, financing with LVR, resumability, personalization, empathy.
#     Be inclusive, compliant with ACL, NCCP, APP. Provide indicative guidance only.
#     Support languages: English, Mandarin, Arabic, Hindi, etc. Respond in selected language.
#     Use name if available. Adapt tone.
#     For finance: Use LVR calculation - call internal API if needed (but simulate here).
#     Present 4-8 vehicle matches from inventory.
#     Allow exploration, comparison, refinement.
#     On selection: Verify, collect docs (prompt for upload), handoff to broker.
#     Additional: Trade-in, insurance, tips.
#     Escalate to human if complex.
#     Allow language switching.
#     State: {state.dict()}
#     If resuming: Welcome back and reference last discussion.
#     """
#     messages = [
#         {"role": "system", "content": system_prompt},
#         *state.history,
#         {"role": "user", "content": user_message}
#     ]
#     url = "https://api.x.ai/v1/chat/completions"
#     headers = {
#         "Authorization": f"Bearer {XAI_API_KEY}",
#         "Content-Type": "application/json"
#     }
#     data = {
#         "model": "grok-3",
#         "messages": messages,
#         "temperature": 0.7,
#         "max_tokens": 500
#     }
#     response = requests.post(url, headers=headers, json=data)
#     if response.status_code == 200:
#         ai_reply = response.json()["choices"][0]["message"]["content"]
#         state.history.append({"role": "user", "content": user_message})
#         state.history.append({"role": "assistant", "content": ai_reply})
#         return ai_reply
#     raise HTTPException(status_code=500, detail="AI response failed")

# # Web Chat Endpoint (for chatbot widget)
# @app.post("/chat")
# async def web_chat(message: Message):
#     state_doc = await conversations.find_one({"phone": message.phone})
#     if state_doc:
#         state = ConversationState(**state_doc)
#         state.last_message_time = state.last_message_time.replace(tzinfo=timezone.utc) if state.last_message_time.tzinfo is None else state.last_message_time
#         if (datetime.now(timezone.utc) - state.last_message_time).total_seconds() > 3600:
#             welcome_back = f"Welcome back, {state.name or 'there'}! Last time we were looking at {state.path or 'car options'}."
#             message.body = welcome_back + " " + message.body
#     else:
#         state = ConversationState(phone=message.phone)
    
#     try:
#         reply = await generate_ai_response(state, message.body)
#     except Exception as e:
#         reply = "Sorry, something went wrong. Please try again."

#     state.last_message_time = datetime.now(timezone.utc)
#     await conversations.replace_one({"phone": message.phone}, state.dict(), upsert=True)

#     if "handoff" in reply.lower() or "broker" in reply.lower():
#         lead = {
#             "phone": message.phone,
#             "state": state.dict(),
#             "timestamp": datetime.now(timezone.utc)
#         }
#         await leads.insert_one(lead)
#         print("Handoff to broker:", lead)
#         reply += " Connecting you to a broker soon."

#     return {"reply": reply}

# @app.post("/lvr", response_model=Dict)
# def get_lvr(input: LVRInput):
#     return calculate_lvr(input.vehicle_value, input.loan_amount)


# @app.get("/vehicles")
# async def get_vehicles(
#     path: str,
#     budget_min: Optional[float] = None,
#     budget_max: Optional[float] = None,
#     interest: Optional[str] = None,
#     page: int = Query(1, ge=1),
#     page_size: int = Query(8, ge=1, le=50)
# ):
#     criteria = {}

#     if budget_min is not None:
#         criteria["min_price"] = budget_min
#     if budget_max is not None:
#         criteria["max_price"] = budget_max
#     if interest:
#         criteria["interest"] = interest

#     vehicles, total = await fetch_vehicles(path, criteria, page, page_size)

#     return {
#         "page": page,
#         "page_size": page_size,
#         "total_results": total,
#         "total_pages": (total + page_size - 1) // page_size,
#         "vehicles": vehicles
#     }

# @app.get("/vehicles/{vehicle_id}")
# async def get_vehicle(vehicle_id: str):
#     try:
#         vehicle = await lots_collection.find_one({"_id": ObjectId(vehicle_id)})
#         if not vehicle:
#             raise HTTPException(status_code=404, detail="Vehicle not found")
#         return dict(vehicle, _id=str(vehicle["_id"]))
#     except Exception as e:
#         raise HTTPException(status_code=400, detail="Invalid vehicle ID")
# @app.post("/upload/{phone}")
# async def upload_document(phone: str, file: UploadFile = File(...)):
#     if not await conversations.find_one({"phone": phone}):
#         raise HTTPException(403, "No active session")
    
#     os.makedirs(f"uploads/{phone}", exist_ok=True)
#     file_path = f"uploads/{phone}/{file.filename}"
#     with open(file_path, "wb") as f:
#         f.write(await file.read())
    
#     meta = {
#         "phone": phone,
#         "file_name": file.filename,
#         "path": file_path,
#         "timestamp": datetime.now(timezone.utc)
#     }
#     await uploads.insert_one(meta)
#     return {"status": "uploaded", "file": file.filename}

# @app.get("/leads")
# async def get_leads():
#     lead_list = []
#     async for lead in leads.find():
#         lead["_id"] = str(lead["_id"])
#         lead_list.append(lead)
#     return {"leads": lead_list}

# @app.get("/")
# def health():
#     return {"status": "healthy"}

# @app.post("/scrape")
# def scrape_endpoint():
#     scrape_all()
#     return {"message": "Scraping completed"}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)


# final
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from fastapi import Query

from typing import Optional, Dict, Any
import requests
import datetime
from bson import ObjectId
from fastapi.openapi.utils import get_openapi
from bs4 import BeautifulSoup
import re
import time
import uuid
from datetime import datetime, timezone, timedelta
from dateutil.parser import parse
import platform
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from apscheduler.schedulers.background import BackgroundScheduler
from math import ceil
from urllib.parse import urljoin
import pymongo
from fastapi.middleware.cors import CORSMiddleware
load_dotenv()

# Environment Variables
XAI_API_KEY = os.getenv("XAI_API_KEY")
REDBOOK_API_KEY = os.getenv("REDBOOK_API_KEY")  # Kept but not used
MONGO_URI = os.getenv("MONGO_URI")

# FastAPI App
app = FastAPI(title="Best Next Car Backend - Chatbot Focus")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Custom OpenAPI schema (optional, for customization)
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version="1.0.0",
        description="API for the Best Next Car chatbot backend",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# MongoDB Client (async for endpoints)
client = AsyncIOMotorClient(MONGO_URI)
db = client.get_default_database()
conversations = db.conversations  # Collection for conversation states
leads = db.leads  # Collection for prequalified leads
uploads = db.uploads  # Collection for document metadata
lots_collection = db.lots  # Current and upcoming lots
sold_collection = db.sold  # Sold archive

# Sync MongoDB Client for scraping
sync_client = pymongo.MongoClient(MONGO_URI)
sync_db = sync_client.get_default_database()
sync_lots_collection = sync_db.lots
sync_sold_collection = sync_db.sold

# Create indexes for fast queries
sync_lots_collection.create_index([('auction_date', 1), ('source', 1), ('make', 1), ('model', 1), ('location', 1), ('scrape_time', 1)])
sync_sold_collection.create_index([('auction_date', 1), ('source', 1), ('make', 1), ('model', 1), ('location', 1)])

# Buyers Premiums (approximate percentages, update as needed)
house_premiums = {
    'tradinggarage': 0.12,
    'carbids': 0.15,
    'collectingcars': 0.06,
    'bennettsclassicauctions': 0.125,
    'burnsandco': 0.15,
    'lloydsonline': 0.20,
    'seven82motors': 0.10,
    'chicaneauctions': 0.12,
    'doningtonauctions': 0.125
}

# Scraping Sources
SOURCES = [
    {'url': 'https://www.tradinggarage.com', 'name': 'tradinggarage'},
    {'url': 'https://collectingcars.com/buy?refinementList%5BlistingStage%5D%5B0%5D=live&refinementList%5BregionCode%5D%5B0%5D=APAC&refinementList%5BcountryCode%5D%5B0%5D=AU', 'name': 'collectingcars'},
    {'url': 'https://www.bennettsclassicauctions.com.au', 'name': 'bennettsclassicauctions'},
    {'url': 'https://carbids.com.au/t/unique-and-classic-car-auctions#!?page=1&count=96&filter%5BDisplay%5D=true', 'name': 'carbids'},
    {'url': 'https://www.lloydsonline.com.au/AuctionLots.aspx?stype=0&stypeid=0&cid=410&smode=0', 'name': 'lloydsonline'},
    {'url': 'https://www.chicaneauctions.com.au', 'name': 'chicaneauctions'},
    {'url': 'https://www.seven82motors.com.au', 'name': 'seven82motors'},
    # Add others if needed
]

# Pydantic Models
class Message(BaseModel):
    phone: str  # Used as session identifier
    body: str

class LVRInput(BaseModel):
    vehicle_value: float
    loan_amount: float

class ConversationState(BaseModel):
    phone: str
    language: str = "English"
    path: Optional[str] = None  # "preowned" or "new"
    name: Optional[str] = None
    budget: Optional[Dict[str, float]] = None  # {"min": float, "max": float}
    finance_needed: bool = False
    income_bracket: Optional[str] = None
    employment_status: Optional[str] = None
    commitments: Optional[str] = None
    loan_term: Optional[int] = None
    down_payment: Optional[float] = None
    vehicle_interest: Optional[str] = None  # For new path
    specs: Optional[Dict[str, str]] = None  # Fuel type, etc.
    selected_vehicle: Optional[Dict] = None
    last_message_time: datetime = datetime.now(timezone.utc)
    history: list = []  # List of {"role": "user/system", "content": str}

# LVR Calculation (as per scope)
def calculate_lvr(vehicle_value: float, loan_amount: float) -> Dict[str, Any]:
    if vehicle_value <= 0:
        return {"lvr_percent": 0, "tier": "invalid"}
    lvr = (loan_amount / vehicle_value) * 100
    if lvr <= 100:
        tier = "preferred"
    elif lvr <= 130:
        tier = "acceptable"
    else:
        tier = "high_risk"
    return {"lvr_percent": round(lvr, 1), "tier": tier}

def get_driver():
    options = Options()
    options.add_argument('--headless')  # Modern way to set headless mode
    options.add_argument('--disable-gpu')  # Often needed for headless
    options.add_argument('--window-size=1920,1080')  # Avoids some rendering issues
    if platform.system() == 'Linux':
        options.add_argument('--no-sandbox')  # Critical for Linux servers
        options.add_argument('--disable-dev-shm-usage')  # Handles small /dev/shm in containers
        options.add_argument('--remote-debugging-port=9222')  # For stability in some envs
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def parse_price(price_str):
    if not price_str or price_str == 'TBA':
        return None
    try:
        if isinstance(price_str, (int, float)):
            val = float(price_str)
            return {'low': val, 'high': val}
        price_str = str(price_str).replace(',', '').replace('$', '').strip()
        m = re.match(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)', price_str)
        if m:
            return {'low': float(m.group(1)), 'high': float(m.group(2))}
        m = re.match(r'(\d+(?:\.\d+)?)', price_str)
        if m:
            val = float(m.group(1))
            return {'low': val, 'high': val}
    except:
        pass
    return None

def scrape_site(source):
    url = source['url']
    name = source['name']
    if name == 'bennettsclassicauctions':
        return scrape_bennetts(url)
    elif name == 'burnsandco':
        return scrape_burnsandco(url)
    elif name == 'carbids':
        return scrape_carbids(url)
    elif name == 'tradinggarage':
        return scrape_tradinggarage(url)
    elif name == 'collectingcars':
        return scrape_collectingcars()
    elif name == 'lloydsonline':
        return scrape_lloydsonline()
    elif name == 'chicaneauctions':
        return scrape_chicane()
    elif name == 'seven82motors':
        return scrape_seven82motors()
    else:
        # Generic scraper for other sites
        try:
            driver = get_driver()
            driver.get(url)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            driver.quit()
            listings = []
            item_class = 'auction-item' # Adjust per site as needed
            for item in soup.find_all('div', class_=item_class):
                lot = parse_lot(item, url)
                if lot and is_classic(lot):
                    lot['source'] = name
                    listings.append(lot)
            return listings
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return []

def scrape_tradinggarage(base_url="https://www.tradinggarage.com"):
    listings = []
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Referer': 'https://www.tradinggarage.com/',
    })
    endpoints = {
        'live': 'https://portal.tradinggarage.com/api/v1/auctions?status=live',
        'coming_soon': 'https://portal.tradinggarage.com/api/v1/auctions?status=coming_soon'
    }
    for status, api_url in endpoints.items():
        try:
            r = session.get(api_url, timeout=12)
            if r.status_code != 200:
                continue
            data = r.json()
            auctions = data.get('data', []) or data.get('auctions', []) or []
            for auction in auctions:
                if auction.get('object_type') != 'vehicle':
                    continue
                title = auction.get('title', 'Unknown Car')
                year_str = ''
                make = ''
                model = ''
                m = re.search(r'(\d{4})\s*([a-zA-Z0-9\-() ]+)\s+(.+)', title)
                if m:
                    year_str = m.group(1)
                    make = m.group(2).strip()
                    model = m.group(3).strip()
                try:
                    year = int(year_str)
                except:
                    year = 0
                price_str = auction.get('last_bid', '0')
                auction_date = None
                try:
                    auction_date = parse(auction['auction_end_at'])
                except:
                    pass
                images = [auction.get('title_image', '')]
                url = f"https://www.tradinggarage.com/products/{auction.get('slug', '')}"
                reserve = 'No' if auction.get('no_reserve', False) else 'Yes'
                location = 'Online / Melbourne'
                description = ''
                odometer = ''
                lot = {
                    'source': 'tradinggarage',
                    'status': auction['status']['name'],
                    'auction_id': auction['id'],
                    'title': title,
                    'year': year,
                    'make': make,
                    'model': model,
                    'odometer': odometer,
                    'price_range': parse_price(price_str),
                    'auction_date': auction_date,
                    'location': location,
                    'images': images,
                    'url': url,
                    'description': description,
                    'reserve': reserve,
                    'scrape_time': datetime.now(timezone.utc)
                }
                # if is_classic(lot):
                listings.append(lot)
        except Exception as e:
            pass
    return listings

def scrape_collectingcars():
    listings = []
    api_url = "https://dora.production.collecting.com/multi_search"
    headers = {
        'x-typesense-api-key': 'aKIufK0SfYHMRp9mUBkZPR7pksehPBZq',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Referer': 'https://collectingcars.com/',
    }
    base_payload = {
        "searches": [
            {
                "query_by": "title,productMake,vehicleMake,productYear,tags,lotType,driveSide,location,collectionId,modelId",
                "query_by_weights": "9,8,7,6,5,4,3,2,1,0",
                "text_match_type": "sum_score",
                "sort_by": "rank:asc",
                "highlight_full_fields": "*",
                "facet_by": "lotType, regionCode, countryCode, saleFormat, noReserve, isBoosted, productMake, vendorType, driveSide, listingStage, tags",
                "max_facet_values": 999,
                "facet_counts": True,
                "facet_stats": True,
                "facet_distribution": True,
                "facet_return_parent": True,
                "collection": "production_cars",
                "q": "*",
                "filter_by": "listingStage:=[`live`] && countryCode:=[`AU`] && regionCode:=[`APAC`]",
                "page": 1,
                "per_page": 50
            }
        ]
    }
    page = 1
    while True:
        base_payload["searches"][0]["page"] = page
        try:
            response = requests.post(api_url, headers=headers, json=base_payload, timeout=15)
            if response.status_code != 200:
                break
            data = response.json()
            if "results" not in data or not data["results"]:
                break
            result = data["results"][0]
            hits = result.get("hits", [])
            if not hits:
                break
            for hit in hits:
                doc = hit.get("document", {})
                if doc.get('lotType') != 'car':
                    continue
                title = doc.get('title', 'Unknown Car')
                year_str = doc.get('productYear', '')
                try:
                    year = int(year_str)
                except:
                    year = 0
                make = doc.get('productMake', '') or doc.get('vehicleMake', '')
                model = doc.get('modelName', '') + ' ' + doc.get('variantName', '').strip()
                price_str = doc.get('currentBid', 0)
                auction_date = None
                try:
                    auction_date = parse(doc['dtStageEndsUTC'])
                except:
                    pass
                images = [doc.get('mainImageUrl', '')]
                url = f"https://collectingcars.com/for-sale/{doc.get('slug', '')}"
                reserve = 'No' if doc.get('noReserve') == "true" else 'Yes'
                location = doc.get('location', 'Australia')
                description = '' # No description in data
                odometer = doc['features'].get('mileage', '')
                transmission = doc['features'].get('transmission', extract_transmission(title))
                body_style = extract_body_style(title)
                fuel_type = doc['features'].get('fuelType', '')
                lot = {
                    'source': 'collectingcars',
                    'status': doc['listingStage'],
                    'auction_id': doc['auctionId'],
                    'title': title,
                    'year': year,
                    'make': make,
                    'model': model,
                    'odometer': odometer,
                    'price_range': parse_price(price_str),
                    'auction_date': auction_date,
                    'location': location,
                    'images': images,
                    'url': url,
                    'description': description,
                    'reserve': reserve,
                    'body_style': body_style,
                    'transmission': transmission,
                    'fuel_type': fuel_type,
                    'scrape_time': datetime.now(timezone.utc)
                }
                # if is_classic(lot):
                listings.append(lot)
            page += 1
            time.sleep(1.2)
        except Exception as e:
            break
    return listings

def scrape_chicane(url='https://www.chicaneauctions.com.au/february-2026-classic-car-auction/'):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"Error fetching Chicane page: {e}")
        return []
    soup = BeautifulSoup(resp.text, 'html.parser')
    listings = []
    base_url = 'https://www.chicaneauctions.com.au'
    for item in soup.select('.promo_box'):
        try:
            button = item.select_one('.desc_wrapper .button')
            link = button if button else item.select_one('.desc_wrapper a')
            if not link:
                continue
            relative_href = link.get('href', '').strip()
            if not relative_href:
                continue
            full_url = relative_href if relative_href.startswith('http') else base_url + relative_href
            if '/sell/' in full_url.lower():
                continue
            title_tag = item.select_one('.desc_wrapper .title')
            title = title_tag.get_text(strip=True) if title_tag else ''
            if not title:
                continue
            title_upper = title.upper()
            if '- OPEN POSITION -' in title_upper or 'STAY TUNED' in title_upper:
                continue
            img_tag = item.select_one('.photo_wrapper img')
            img_src = None
            if img_tag:
                img_src = img_tag.get('data-src') or img_tag.get('src')
                if img_src and img_src.startswith('//'):
                    img_src = 'https:' + img_src
            if not img_src or 'upcoming-classic-car-auction-house.png' in img_src:
                continue
            images = [img_src] if img_src else []
            lot_num = None
            m = re.search(r'(?:lot[-_\s]*)(\d+)', full_url, re.IGNORECASE)
            if m:
                lot_num = m.group(1)
            if not lot_num:
                m = re.search(r'(?:lot|Lot|LOT)\s*(\d+)', title, re.IGNORECASE)
                if m:
                    lot_num = m.group(1)
            year = None
            make = ''
            model = ''
            m = re.match(r'^(\d{4})\s+([A-Za-z0-9\-]+(?:\s+[A-Za-z0-9\-]+)*?)(?:\s+(.+?))?(?:\s*-|$)', title.strip())
            if m:
                try:
                    year = int(m.group(1))
                except:
                    pass
                make = (m.group(2) or '').strip()
                model = (m.group(3) or '').strip()
            if not year:
                ym = re.search(r'\b(19\d{2}|20\d{2})\b', title)
                if ym:
                    year = int(ym.group(1))
            location = {
                'city': 'Melbourne',
                'state': 'VIC',
                'country': 'Australia'
            }
            lot = {
                'source': 'chicaneauctions',
                'auction_id': lot_num or title.lower().replace(' ', '-').replace('--', '-'),
                'title': title,
                'url': full_url,
                'year': year,
                'make': make,
                'model': model,
                'vehicle': {
                    'year': year,
                    'make': make,
                    'model': model,
                },
                'price': {
                    'current': None,  # not shown on pre-catalogue
                    'reserve': 'Unknown',
                },
                'auction_end': None,  # not shown yet
                'location': location,
                'images': images,
                'condition': {
                    'comment': title,  # can be improved later from detail page
                },
                'status': 'upcoming',
                'scrape_time': datetime.now(timezone.utc).isoformat(),
            }
            # if is_classic(lot):
            listings.append(lot)
        except Exception as e:
            print(f"Error parsing one Chicane promo_box: {e}")
            continue
    return listings

def scrape_lloydsonline(url='https://www.lloydsonline.com.au/AuctionLots.aspx?stype=0&stypeid=0&cid=410&smode=0'):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code != 200:
            print(f"Lloyds returned {resp.status_code}")
            return []
        html_content = resp.text
    except Exception as e:
        print(f"Error fetching Lloyds: {e}")
        return []
    soup = BeautifulSoup(html_content, 'html.parser')
    listings = []
    base_url = 'https://www.lloydsonline.com.au'
    for item in soup.select('.gallery_item.lot_list_item'):
        try:
            link = item.select_one('a[href^="LotDetails.aspx"]')
            relative_href = link.get('href') if link else None
            full_url = None
            if relative_href:
                full_url = base_url + '/' + relative_href.lstrip('/')
            lot_num_elem = item.select_one('.lot_num')
            lot_num = lot_num_elem.text.strip() if lot_num_elem else None
            img_tag = item.select_one('.lot_img img')
            img_src = None
            if img_tag and img_tag.has_attr('src'):
                img_src = img_tag['src'].strip()
                if img_src.startswith('//'):
                    img_src = 'https:' + img_src
            images = [img_src] if img_src else []
            desc_elem = item.select_one('.lot_desc')
            title = desc_elem.get_text(strip=True) if desc_elem else ''
            year = None
            make = ''
            model = ''
            m = re.match(r'^(\d{4})\s+(.+?)\s+(.+?)(?:\s+|$)', title)
            if m:
                try:
                    year = int(m.group(1))
                except ValueError:
                    pass
                make = m.group(2).strip()
                model = m.group(3).strip()
            bid_tag = item.select_one('.lot_cur_bid span, .lot_bidding span')
            current_bid_str = bid_tag.get_text(strip=True) if bid_tag else '0'
            current_bid = None
            try:
                current_bid = float(re.sub(r'[^\d.]', '', current_bid_str))
            except (ValueError, TypeError):
                pass
            time_rem_tag = item.select_one('[data-seconds_rem]')
            seconds_rem = 0
            if time_rem_tag and time_rem_tag.has_attr('data-seconds_rem'):
                try:
                    seconds_rem = int(time_rem_tag['data-seconds_rem'])
                except ValueError:
                    pass
            auction_end = datetime.now(timezone.utc) + timedelta(seconds=seconds_rem) if seconds_rem > 0 else None
            location_img = item.select_one('.auctioneer-location img')
            state_src = location_img.get('src', '').split('/')[-1] if location_img else ''
            state_map = {
                's_1.png': 'ACT', 's_2.png': 'NT', 's_3.png': 'NSW',
                's_4.png': 'QLD', 's_5.png': 'SA', 's_6.png': 'TAS',
                's_7.png': 'WA', 's_8.png': 'VIC',
            }
            state = state_map.get(state_src, '')
            location = {'state': state}
            unreserved = item.select_one('.sash.ribbon-blue')
            reserve = 'No' if unreserved and 'UNRESERVED' in (unreserved.get_text(strip=True) or '').upper() else 'Yes'
            vehicle = {
                'year': year,
                'make': make,
                'model': model,
            }
            price = {
                'current': current_bid,
            }
            condition = {
                'comment': title,
            }
            lot = {
                'source': 'lloydsonline',
                'auction_id': lot_num,  # or use data-lot_id if available
                'title': title,
                'url': full_url,
                'year': year,
                'make': make,
                'model': model,
                'vehicle': vehicle,
                'price': price,
                'auction_end': auction_end,
                'location': location,
                'images': images,
                'condition': condition,
                'reserve': reserve,
                'status': 'live' if seconds_rem > 0 else 'ended',
                'scrape_time': datetime.now(timezone.utc),
            }
            # if is_classic(lot):
            listings.append(lot)
        except Exception as e:
            print(f"Error parsing Lloyds lot: {str(e)}")
    return listings

def scrape_carbids_api():
    listings = []
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://carbids.com.au/',
        'Origin': 'https://carbids.com.au',
    })
    try:
        home = session.get("https://carbids.com.au/t/unique-and-classic-car-auctions")
        soup = BeautifulSoup(home.text, 'html.parser')
        token_input = soup.find('input', {'name': '__RequestVerificationToken'})
        if token_input and token_input.get('value'):
            session.headers['__RequestVerificationToken'] = token_input['value']
    except:
        pass
    page = 0
    while True:
        payload = {
            "top": 96,
            "skip": page * 96,
            "sort": {"aucClose": "asc"},
            "tagName": "Unique and Classic Car Auctions",
            "filter": {"Display": True}
        }
        try:
            resp = session.post(
                "https://carbids.com.au/Search/Tags",
                json=payload,
                timeout=20
            )
            if resp.status_code != 200:
                print(f"Carbids API returned {resp.status_code}")
                break
            data = resp.json()
            auctions = data.get("auctions", [])
            if not auctions:
                break
            for auc in auctions:
                title = auc.get("aucTitle", "").strip()
                title_text = auc.get("aucTitleText", title).strip()
                short_title = auc.get("aucTitleShortText", title).strip()
                year = None
                make = ""
                model = ""
                m = re.match(r'^(\d{1,2}/)?(\d{4})\s+(.+?)\s+(.+?)(?:\s+|$)', title_text)
                if m:
                    year_str = m.group(2)
                    make = m.group(3).strip()
                    model = m.group(4).strip()
                    try:
                        year = int(year_str)
                    except:
                        year = None
                if not year and auc.get("aucYear"):
                    try:
                        year = int(auc["aucYear"])
                    except:
                        pass
                make = auc.get("aucMake", make).strip()
                model = auc.get("aucModel", model).strip()
                current_bid = auc.get("aucCurrentBid", 0.0)
                starting_bid = auc.get("aucStartingBid", 1.0)
                price_info = {
                    "current": float(current_bid) if current_bid else None,
                    "starting": float(starting_bid) if starting_bid else None,
                    "increment": auc.get("aucBidIncrement", 0.0),
                    "buyers_premium_text": auc.get("aucBPText", ""),
                    "gst_note": auc.get("isGstApplicableWording", "")
                }
                end_date_str = auc.get("aucCloseUtc")
                auction_end = None
                if end_date_str:
                    try:
                        auction_end = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                    except:
                        try:
                            auction_end = parse(end_date_str)
                        except:
                            pass
                location = {
                    "city": auc.get("aucCity", ""),
                    "state": auc.get("aucState", ""),
                    "address": auc.get("aucAddressLocation", ""),
                    "pickup": auc.get("aucPickupAvailable", False),
                    "freight": auc.get("aucFreightAvailable", False),
                    "freight_limits": auc.get("aucItemFreightLimits", "")
                }
                vehicle = {
                    "year": year,
                    "make": make,
                    "model": model,
                    "odometer_km": auc.get("aucOdometerNumber"),
                    "odometer_display": auc.get("aucOdometer", ""),
                    "transmission": auc.get("aucTransmission"),
                    "fuel_type": auc.get("aucFuelType"),
                    "engine_capacity": auc.get("aucCapacity"),
                    "cylinders": auc.get("aucCylinder"),
                    "drivetrain": auc.get("aucDrv"),
                }
                images = []
                base = auc.get("aucCarsThumbnailUrl", auc.get("aucThumbnailUrl", ""))
                if base:
                    images.append(base)
                for size in ["small", "medium", "large"]:
                    key = f"aucCars{size.capitalize()}ThumbnailUrl"
                    if auc.get(key):
                        images.append(auc[key])
                medium_list = auc.get("aucMediumThumbnailUrlList", [])
                images.extend([url for url in medium_list if url])
                condition = {
                    "body": auc.get("aucBodyCondition"),
                    "paint": auc.get("aucPaintCondition"),
                    "features_text": auc.get("aucFeaturesText"),
                    "key_facts": auc.get("aucKeyFactsText"),
                    "comment": auc.get("aucComment"),
                    "service_history": auc.get("aucServiceHistory"),
                }
                lot = {
                    "source": "carbids",
                    "auction_id": auc.get("aucID"),
                    "reference_number": auc.get("aucReferenceNo"),
                    "title": title_text,
                    "short_title": short_title,
                    "url": "https://carbids.com.au/" + auc.get("AucDetailsUrlLink", "").lstrip("/"),
                    "year": year,
                    "make": make,
                    "model": model,
                    "vehicle": vehicle,
                    "price": price_info,
                    "auction_end": auction_end,
                    "location": location,
                    "images": images[:8], # limit to 8 for storage
                    "condition": condition,
                    "reserve": "Yes", # currently no reserve field → assume Yes
                    "status": "live", # we only get live auctions here
                    "scrape_time": datetime.now(timezone.utc),
                }
                # if is_classic(lot):
                listings.append(lot)
            page += 1
            time.sleep(1.3) # polite delay
        except Exception as e:
            print("Error in carbids API loop:", str(e))
            break
    return listings

def scrape_carbids(base_url):
    listings_api = scrape_carbids_api()
    combined = listings_api
    seen_urls = set()
    unique = []
    for lot in combined:
        u = lot.get("url")
        if u and u not in seen_urls:
            seen_urls.add(u)
            unique.append(lot)
    return unique

def scrape_bennetts(base_url="https://www.bennettsclassicauctions.com.au"):
    pages = [base_url, base_url + '/off-site.php']
    all_listings = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    for page_url in pages:
        try:
            resp = requests.get(page_url, headers=headers, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            sitename = soup.find('div', id='sitename')
            h3 = sitename.find('h3') if sitename else None
            auction_text = h3.text.strip() if h3 else ''
            date_match = re.search(r'(\d{1,2}[ST|ND|RD|TH]{0,2} \w+ \d{4})', auction_text.upper())
            time_match = re.search(r'@ (\d{1,2}[AP]M)', auction_text.upper())
            auction_date_str = ''
            if date_match:
                date_str = re.sub(r'([ST|ND|RD|TH])', '', date_match.group(1))
                auction_date_str += date_str
            if time_match:
                auction_date_str += ' ' + time_match.group(1)
            auction_date = None
            try:
                auction_date = parse(auction_date_str)
            except:
                pass
            sections = soup.find_all('div', class_='clear')
            for section in sections:
                column = section.find('div', class_='column column-600 column-left')
                if column:
                    h3_cat = column.find('h3')
                    category = h3_cat.text.strip() if h3_cat else ''
                    table = column.find('table')
                    if table:
                        tbody = table.find('tbody')
                        trs = tbody.find_all('tr') if tbody else table.find_all('tr')
                        for tr in trs[1:]:  # Skip header
                            tds = tr.find_all('td')
                            if len(tds) >= 7:  # Ensure enough columns
                                photo_td = tds[0]
                                a = photo_td.find('a')
                                detail_url = base_url + '/' + a['href'].lstrip('/') if a else ''
                                img = photo_td.find('img')
                                image_src = base_url + '/' + img['src'].lstrip('/') if img and img['src'].startswith('images') else (img['src'] if img else '')
                                make = tds[1].text.strip()
                                stock_model = tds[2].text.strip()
                                parts = stock_model.split('/')
                                stock_ref = parts[0].strip() if parts else ''
                                model = parts[1].strip() if len(parts) > 1 else stock_model
                                year_str = tds[3].text.strip()
                                try:
                                    year = int(year_str)
                                except:
                                    year = 0
                                options = tds[4].text.strip()
                                location_td = tds[5]
                                location = location_td.text.strip().replace('\n', '').replace('br /', '')
                                lot = {
                                    'source': 'bennettsclassicauctions',
                                    'make': make,
                                    'model': model,
                                    'year': year,
                                    'price_range': None,
                                    'auction_date': auction_date,
                                    'location': location,
                                    'images': [image_src] if image_src else [],
                                    'url': detail_url,
                                    'description': options,
                                    'reserve': 'Yes',
                                    'body_style': extract_body_style(options),
                                    'transmission': extract_transmission(options),
                                    'scrape_time': datetime.now(timezone.utc)
                                }
                                # if is_classic(lot):
                                all_listings.append(lot)
        except Exception as e:
            print(f"Error scraping Bennetts ({page_url}): {str(e)}")
    return all_listings

def scrape_burnsandco(base_url="https://burnsandcoauctions.com.au"):
    pages = [base_url + '/current-auctions/', base_url + '/upcoming-auctions/']
    all_listings = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    for page_url in pages:
        try:
            resp = requests.get(page_url, headers=headers, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            articles = soup.find_all('article', class_='regular masonry-blog-item')
            for article in articles:
                img_link = article.find('a', class_='img-link')
                detail_url = img_link['href'] if img_link else ''
                img = img_link.find('img') if img_link else None
                image_src = img['src'] if img else ''
                meta_category = article.find('span', class_='meta-category')
                category = meta_category.text.strip() if meta_category else ''
                date_item = article.find('span', class_='date-item')
                auction_date_str = date_item.text.strip() if date_item else ''
                auction_date = None
                try:
                    auction_date = parse(auction_date_str)
                except:
                    pass
                title_a = article.find('h3', class_='title').find('a') if article.find('h3', class_='title') else None
                title = title_a.text.strip() if title_a else ''
                excerpt = article.find('div', class_='excerpt').text.strip() if article.find('div', class_='excerpt') else ''
                place = article.find('p', class_='place').text.strip() if article.find('p', class_='place') else ''
                bid_links = article.find_all('p', class_='registration_bidding_link')
                for bid_p in bid_links:
                    bid_a = bid_p.find('a')
                    bid_url = bid_a['href'] if bid_a else ''
                    catalogue_lots = scrape_catalogue(bid_url)
                    for cat_lot in catalogue_lots:
                        cat_lot['auction_date'] = auction_date or cat_lot.get('auction_date')
                        cat_lot['location'] = place or cat_lot.get('location')
                        cat_lot['source'] = 'burnsandco'
                        all_listings.append(cat_lot)
        except Exception as e:
            print(f"Error scraping Burns and Co ({page_url}): {str(e)}")
    return all_listings

def scrape_seven82motors():
    listings = []
    auction_slug = "march-29th-2026"
    api_url = f"https://seven82-json-sb.manage.auction/listings/auctions/{auction_slug}?amt=100"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Referer': 'https://www.seven82motors.com.au/',
    }
    try:
        resp = requests.get(api_url, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        auction_title = data.get("heading", "Unknown Auction Date")
        auction_date = None
        date_str_candidates = [
            auction_title,
            data.get("breadcrumbs", [{}])[0].get("title", ""),
            f"{auction_title} 2026",
            auction_slug.replace("-", " ").title()
        ]
        for candidate in date_str_candidates:
            if not candidate:
                continue
            try:
                auction_date = parse(candidate, fuzzy=True, dayfirst=False)
                if auction_date.year >= 2025:
                    break
            except:
                continue
        if not auction_date:
            auction_date = datetime.now(timezone.utc) + timedelta(days=60)
        items = data.get("items", [])
        for item in items:
            if item.get("dummy_lot", 0) == 1:
                continue
            title = (item.get("title") or "").strip()
            if not title:
                continue
            if any(phrase in title.upper() for phrase in [
                "SELL YOUR CAR", "CONSIGN", "REGISTER AND BID", "LEARN HOW TO"
            ]):
                continue
            year = None
            make = ""
            model = ""
            clean_title = re.sub(
                r'^(NO RESERVE!?\s*|RARE\s*|FULLY RESTORED\s*|CUSTOM\s*)',
                '', title, flags=re.IGNORECASE
            ).strip()
            m = re.match(r'^(\d{4})\s+(.+?)(?:\s+(.+?))?(?:\s+|$)', clean_title)
            if m:
                try:
                    year = int(m.group(1))
                except:
                    pass
                make_model_part = (m.group(2) or "").strip()
                extra = (m.group(3) or "").strip()
                parts = make_model_part.split(maxsplit=1)
                if parts:
                    make = parts[0].strip()
                    if len(parts) > 1:
                        model = parts[1].strip()
                    model = f"{model} {extra}".strip()
            reserve = "No" if "NO RESERVE" in title.upper() else "Yes"
            images = []
            featured = item.get("media_featured", [])
            if isinstance(featured, list):
                for img_obj in featured:
                    if isinstance(img_obj, dict):
                        src = img_obj.get("src")
                        if src and "catalog/" in src:
                            clean_src = src.lstrip('/')
                            full_url = f"https://seven82motors.mymedia.delivery/{clean_src}"
                            if full_url not in images:
                                images.append(full_url)
            main_img = item.get("image")
            if main_img and "catalog/" in main_img:
                clean_main = main_img.lstrip('/')
                full_main = f"https://seven82motors.mymedia.delivery/{clean_main}"
                if full_main not in images:
                    images.insert(0, full_main)
            seen = set()
            clean_images = []
            for url in images:
                if url and url not in seen:
                    seen.add(url)
                    if not any(x in url.lower() for x in ["thumb", "small", "placeholder", "watermark"]):
                        clean_images.append(url)
            images = clean_images[:12]
            is_coming_soon = False
            coming_soon_data = item.get("coming_soon", [])
            if isinstance(coming_soon_data, list):
                for entry in coming_soon_data:
                    if isinstance(entry, dict):
                        if entry.get("settings", {}).get("coming_soon") in (True, "1", 1, "true"):
                            is_coming_soon = True
                            break
            lot_path = item.get('path', '').lstrip('/')
            lot_url = f"https://www.seven82motors.com.au/lot/{lot_path}" if lot_path else ""
            lot = {
                'source': 'seven82motors',
                'status': 'upcoming',
                'auction_id': item.get("id"),
                'lot_number': item.get("number"),
                'title': title,
                'year': year,
                'make': make,
                'model': model,
                'odometer': None,  # detail page only
                'price_range': None,  # not in list view
                'auction_date': auction_date,
                'location': "Brisbane, QLD (Online)",
                'images': images,
                'url': lot_url,
                'description': (item.get("description_short") or "").strip(),
                'reserve': reserve,
                'body_style': None,
                'transmission': None,
                'fuel_type': None,
                'scrape_time': datetime.now(timezone.utc),
                'coming_soon': is_coming_soon,
                'buyers_premium_pct': 8.8,
                'auction_title': auction_title,
                'raw_filters': item.get("filters", {}),
            }
            # if is_classic(lot):
            listings.append(lot)
    except Exception as e:
        print(f"[seven82motors] Error scraping {auction_slug}: {e}")
    return listings

def scrape_catalogue(catalogue_url):
    listings = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        resp = requests.get(catalogue_url, headers=headers, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        table = soup.find('table')  # Or find('table', class_='catalogue-table') if specific class
        if table:
            trs = table.find_all('tr')
            for tr in trs[1:]:  # Skip header row
                tds = tr.find_all('td')
                if len(tds) < 4:
                    continue
                lot_number = tds[0].text.strip()
                desc_td = tds[1]
                desc = desc_td.text.strip()
                match = re.match(r'(\d{4})? ?(.*?) (.*)', desc)
                year_str = match.group(1) if match and match.group(1) else ''
                try:
                    year = int(year_str)
                except:
                    year = 0
                make = match.group(2) if match else ''
                model = match.group(3) if match else desc
                images = [urljoin(catalogue_url, img['src']) for img in tr.find_all('img') if 'src' in img.attrs]
                detail_a = desc_td.find('a')
                detail_url = urljoin(catalogue_url, detail_a['href']) if detail_a else ''
                current_bid = tds[2].text.strip()
                lot = {
                    'lot_number': lot_number,
                    'make': make,
                    'model': model,
                    'year': year,
                    'price_range': parse_price(current_bid),
                    'auction_date': None,
                    'location': None,
                    'images': images,
                    'url': detail_url,
                    'description': desc,
                    'reserve': 'Yes',
                    'body_style': extract_body_style(desc),
                    'transmission': extract_transmission(desc),
                    'scrape_time': datetime.now(timezone.utc)
                }
                if is_classic(lot):
                    listings.append(lot)
    except Exception as e:
        print(f"Error scraping catalogue ({catalogue_url}): {str(e)}")
    return listings

def parse_lot(item, url):
    try:
        description = item.find('p', class_='desc') or item.find('div', class_='description')
        description_text = description.text.strip() if description else ''
        year_elem = item.find('span', class_='year') or item.find('h3')
        year_str = year_elem.text.strip() if year_elem else '0'
        try:
            year = int(year_str)
        except:
            year = 0
        make_elem = item.find('span', class_='make') or item.find('h2')
        model_elem = item.find('span', class_='model')
        price_elem = item.find('span', class_='estimate') or item.find('div', class_='price')
        price_str = price_elem.text.strip() if price_elem else None
        date_elem = item.find('span', class_='date')
        location_elem = item.find('span', class_='location')
        link_elem = item.find('a', class_='lot-link') or item.find('a')
        lot = {
            'make': make_elem.text.strip() if make_elem else None,
            'model': model_elem.text.strip() if model_elem else None,
            'year': year,
            'price_range': parse_price(price_str),
            'auction_date': parse_date(date_elem.text.strip()) if date_elem else None,
            'location': location_elem.text.strip() if location_elem else 'Online',
            'images': [img['src'] for img in item.find_all('img', class_='thumbnail')][:6],
            'url': link_elem['href'] if link_elem else url,
            'description': description_text,
            'reserve': 'No' if 'no reserve' in description_text.lower() else 'Yes',
            'body_style': extract_body_style(description_text),
            'transmission': extract_transmission(description_text),
            'scrape_time': datetime.now(timezone.utc)
        }
        return lot
    except:
        return None

def parse_date(date_str):
    try:
        return parse(date_str)
    except:
        return None

def extract_body_style(desc):
    lower_desc = desc.lower()
    styles = ['coupe', 'convertible', 'sedan', 'wagon', 'ute', 'truck']
    for style in styles:
        if style in lower_desc:
            return style.capitalize()
    return None

def extract_transmission(desc):
    lower_desc = desc.lower()
    if 'manual' in lower_desc:
        return 'Manual'
    if 'auto' in lower_desc or 'automatic' in lower_desc:
        return 'Automatic'
    return None

def is_classic(lot):
    year = lot.get('year')
    if year is None or not isinstance(year, (int, float)):
        text = (lot.get('title', '') + ' ' + lot.get('description', '')).lower()
        has_classic_hint = any(word in text for word in [
            'classic', 'muscle', 'vintage', 'hot rod', 'restored', 'collector',
            'holden', 'falcon gt', 'monaro', 'charger', 'mustang', 'corvette'
        ])
        return has_classic_hint
    if year < 2005:
        return True
    text = (lot.get('title', '') + ' ' + lot.get('description', '')).lower()
    modern_classic_keywords = [
        'hellcat', 'demon', 'supercharged', 'stroker', 'r8', 'gts-r', 'boss 302',
        'shelby', 'a9x', 'fpv', 'gtr', 'torana', 'monaro'
    ]
    return any(kw in text for kw in modern_classic_keywords)

def normalize_auction_date(ad):
    if not ad:
        return None
    if isinstance(ad, datetime):
        return ad
    if isinstance(ad, str):
        try:
            return parse(ad)
        except:
            return None
    try:
        return parse(str(ad))
    except:
        return None

# Scrape all and store in DB (sync version)
def scrape_all():
    all_lots = []
    scrape_start = datetime.now(timezone.utc)
    for source in SOURCES:
        lots = scrape_site(source)
        all_lots.extend(lots)
    
    for lot in all_lots:
        lot['scrape_time'] = datetime.now(timezone.utc)
        lot['auction_date'] = normalize_auction_date(lot.get('auction_date'))
        if not lot.get('url'):
            lot['url'] = f"{lot.get('source','unknown')}/{uuid.uuid4()}"
        sync_lots_collection.update_one(
            {'url': lot['url']},
            {'$set': lot, '$setOnInsert': {'first_scraped': scrape_start}},
            upsert=True
        )
    
    now = datetime.now(timezone.utc)
    ended = list(sync_lots_collection.find({'auction_date': {'$lt': now}}))
    for end in ended:
        house = end['source']
        prem = house_premiums.get(house, 0.15)
        hammer = end.get('price_range', {}).get('high', 0)
        total = hammer * (1 + prem)
        sold_doc = dict(end)
        sold_doc['hammer_price'] = hammer
        sold_doc['buyers_premium'] = prem * 100
        sold_doc['total_price'] = total
        sync_sold_collection.insert_one(sold_doc)
        sync_lots_collection.delete_one({'_id': end['_id']})
    
    two_years_ago = now - timedelta(days=730)
    sync_sold_collection.delete_many({'auction_date': {'$lt': two_years_ago}})

# Scheduler for scraping
scheduler = BackgroundScheduler()
scheduler.add_job(scrape_all, 'interval', hours=1)
scheduler.start()



async def fetch_vehicles(path: str, criteria: Dict, page: int, page_size: int):
    if path != "preowned":
        return [], 0

    query = {}

    if "min_price" in criteria:
        query["price_range.low"] = {"$gte": criteria["min_price"]}

    if "max_price" in criteria:
        query["price_range.high"] = {"$lte": criteria["max_price"]}

    if "interest" in criteria:
        interest = criteria["interest"]
        query["$or"] = [
            {"make": {"$regex": interest, "$options": "i"}},
            {"model": {"$regex": interest, "$options": "i"}},
            {"title": {"$regex": interest, "$options": "i"}},
            {"description": {"$regex": interest, "$options": "i"}}
        ]

    # Pagination logic
    skip = (page - 1) * page_size

    total = await lots_collection.count_documents(query)

    cursor = (
        lots_collection
        .find(query)
        .skip(skip)
        .limit(page_size)
    )

    vehicles = await cursor.to_list(length=page_size)

    return [dict(v, _id=str(v["_id"])) for v in vehicles], total
# xAI API Integration for Conversational AI
async def generate_ai_response(state: ConversationState, user_message: str) -> str:
    system_prompt = f"""
    You are an AI car finder for Australian users. Follow the project scope strictly.
    Handle onboarding, language selection, preowned/new paths, financing with LVR, resumability, personalization, empathy.
    Be inclusive, compliant with ACL, NCCP, APP. Provide indicative guidance only.
    Support languages: English, Mandarin, Arabic, Hindi, etc. Respond in selected language.
    Use name if available. Adapt tone.
    For finance: Use LVR calculation - call internal API if needed (but simulate here).
    Present 4-8 vehicle matches from inventory.
    Allow exploration, comparison, refinement.
    On selection: Verify, collect docs (prompt for upload), handoff to broker.
    Additional: Trade-in, insurance, tips.
    Escalate to human if complex.
    Allow language switching.
    State: {state.dict()}
    If resuming: Welcome back and reference last discussion.
    Your responses must be concise, precise, and brief. Keep under 150 words. Avoid unnecessary details. Use bullet points for lists. Be direct.
    """

    # Fetch real inventory if in preowned path
    inventory_str = "No matching vehicles currently available."
    if state.path == "preowned":
        criteria = {}
        if state.budget:
            criteria["min_price"] = state.budget.get("min", 0)
            criteria["max_price"] = state.budget.get("max", float("inf"))
        if state.vehicle_interest:
            criteria["interest"] = state.vehicle_interest
        vehicles, _ = await fetch_vehicles("preowned", criteria, 1, 20)
        if vehicles:
            vehicle_summaries = []
            for v in vehicles:
                price_range = v.get('price_range', {})
                low = price_range.get('low', 'N/A')
                high = price_range.get('high', 'N/A')
                price_str = f"${low}-{high}" if low != high else f"${low}"
                summary = f"{v.get('year', 'N/A')} {v.get('make', 'Unknown')} {v.get('model', 'Unknown')} - {price_str}, {v.get('location', 'N/A')}, {v.get('url', 'N/A')}"
                vehicle_summaries.append(summary)
            inventory_str = "\n".join(vehicle_summaries)

    system_prompt += f"\nWhen suggesting vehicles, use only from the following real inventory lots:\n{inventory_str}"

    messages = [
        {"role": "system", "content": system_prompt},
        *state.history,
        {"role": "user", "content": user_message}
    ]
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "grok-3",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 200
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        ai_reply = response.json()["choices"][0]["message"]["content"]
        state.history.append({"role": "user", "content": user_message})
        state.history.append({"role": "assistant", "content": ai_reply})
        return ai_reply
    raise HTTPException(status_code=500, detail="AI response failed")

# Web Chat Endpoint (for chatbot widget)
@app.post("/chat")
async def web_chat(message: Message):
    state_doc = await conversations.find_one({"phone": message.phone})
    if state_doc:
        state = ConversationState(**state_doc)
        state.last_message_time = state.last_message_time.replace(tzinfo=timezone.utc) if state.last_message_time.tzinfo is None else state.last_message_time
        if (datetime.now(timezone.utc) - state.last_message_time).total_seconds() > 3600:
            welcome_back = f"Welcome back, {state.name or 'there'}! Last time we were looking at {state.path or 'car options'}."
            message.body = welcome_back + " " + message.body
    else:
        state = ConversationState(phone=message.phone)
        state.path = "preowned"  # Set default path to preowned
    
    try:
        reply = await generate_ai_response(state, message.body)
    except Exception as e:
        reply = "Sorry, something went wrong. Please try again."

    state.last_message_time = datetime.now(timezone.utc)
    await conversations.replace_one({"phone": message.phone}, state.dict(), upsert=True)

    if "handoff" in reply.lower() or "broker" in reply.lower():
        lead = {
            "phone": message.phone,
            "state": state.dict(),
            "timestamp": datetime.now(timezone.utc)
        }
        await leads.insert_one(lead)
        print("Handoff to broker:", lead)
        reply += " Connecting you to a broker soon."

    return {"reply": reply}

@app.post("/lvr", response_model=Dict)
def get_lvr(input: LVRInput):
    return calculate_lvr(input.vehicle_value, input.loan_amount)


@app.get("/vehicles")
async def get_vehicles(
    path: str,
    budget_min: Optional[float] = None,
    budget_max: Optional[float] = None,
    interest: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(8, ge=1, le=50)
):
    criteria = {}

    if budget_min is not None:
        criteria["min_price"] = budget_min
    if budget_max is not None:
        criteria["max_price"] = budget_max
    if interest:
        criteria["interest"] = interest

    vehicles, total = await fetch_vehicles(path, criteria, page, page_size)

    return {
        "page": page,
        "page_size": page_size,
        "total_results": total,
        "total_pages": (total + page_size - 1) // page_size,
        "vehicles": vehicles
    }

@app.get("/vehicles/{vehicle_id}")
async def get_vehicle(vehicle_id: str):
    try:
        vehicle = await lots_collection.find_one({"_id": ObjectId(vehicle_id)})
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        return dict(vehicle, _id=str(vehicle["_id"]))
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid vehicle ID")
@app.post("/upload/{phone}")
async def upload_document(phone: str, file: UploadFile = File(...)):
    if not await conversations.find_one({"phone": phone}):
        raise HTTPException(403, "No active session")
    
    os.makedirs(f"uploads/{phone}", exist_ok=True)
    file_path = f"uploads/{phone}/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    meta = {
        "phone": phone,
        "file_name": file.filename,
        "path": file_path,
        "timestamp": datetime.now(timezone.utc)
    }
    await uploads.insert_one(meta)
    return {"status": "uploaded", "file": file.filename}

@app.get("/leads")
async def get_leads():
    lead_list = []
    async for lead in leads.find():
        lead["_id"] = str(lead["_id"])
        lead_list.append(lead)
    return {"leads": lead_list}

@app.get("/")
def health():
    return {"status": "healthy"}

@app.post("/scrape")
def scrape_endpoint():
    scrape_all()
    return {"message": "Scraping completed"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)