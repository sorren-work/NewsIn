"""Weather via open-meteo.com — free, no API key needed."""
import json, os, threading, urllib.parse, urllib.request

WMO = {
    0:"Clear sky",1:"Mainly clear",2:"Partly cloudy",3:"Overcast",
    45:"Foggy",48:"Icy fog",51:"Light drizzle",53:"Drizzle",55:"Heavy drizzle",
    61:"Light rain",63:"Rain",65:"Heavy rain",71:"Light snow",73:"Snow",
    75:"Heavy snow",77:"Snow grains",80:"Rain showers",81:"Showers",
    82:"Heavy showers",85:"Snow showers",86:"Heavy snow showers",
    95:"Thunderstorm",96:"Thunderstorm+hail",99:"Heavy thunderstorm",
}

def wicon(code):
    if code==0: return "☀"
    if code<=2: return "⛅"
    if code<=3: return "☁"
    if code<=48: return "🌫"
    if code<=67: return "🌧"
    if code<=77: return "❄"
    if code<=82: return "🌦"
    if code<=86: return "🌨"
    return "⛈"

# 50+ countries with comprehensive city lists
LOCATIONS = {
    "Nepal": [
        ("Kathmandu",27.7172,85.3240),("Pokhara",28.2096,83.9856),
        ("Biratnagar",26.4525,87.2718),("Lalitpur",27.6644,85.3188),
        ("Bhaktapur",27.6710,85.4298),("Butwal",27.7006,83.4484),
        ("Dharan",26.8120,87.2836),("Birgunj",27.0104,84.8778),
        ("Hetauda",27.4167,85.0333),("Janakpur",26.7288,85.9264),
        ("Nepalgunj",28.0500,81.6167),("Dhangadhi",28.7000,80.5833),
        ("Itahari",26.6618,87.2769),("Lumbini",27.4833,83.2667),
        ("Pokhara-Lekhnath",28.1354,84.0089),
    ],
    "India": [
        ("Delhi",28.6139,77.2090),("Mumbai",19.0760,72.8777),
        ("Bangalore",12.9716,77.5946),("Kolkata",22.5726,88.3639),
        ("Chennai",13.0827,80.2707),("Hyderabad",17.3850,78.4867),
        ("Pune",18.5204,73.8567),("Jaipur",26.9124,75.7873),
        ("Lucknow",26.8467,80.9462),("Ahmedabad",23.0225,72.5714),
        ("Surat",21.1702,72.8311),("Kanpur",26.4499,80.3319),
        ("Nagpur",21.1458,79.0882),("Indore",22.7196,75.8577),
        ("Bhopal",23.2599,77.4126),("Patna",25.5941,85.1376),
        ("Bihar (State)",25.0961,85.3131),("Gaya",24.7964,85.0080),
        ("Muzaffarpur",26.1209,85.3647),("Bhagalpur",25.2425,86.9842),
        ("Agra",27.1767,78.0081),("Vadodara",22.3072,73.1812),
        ("Coimbatore",11.0168,76.9558),("Kochi",9.9312,76.2673),
        ("Visakhapatnam",17.6868,83.2185),("Amritsar",31.6340,74.8723),
        ("Chandigarh",30.7333,76.7794),("Guwahati",26.1445,91.7362),
        ("Thiruvananthapuram",8.5241,76.9366),("Bhubaneswar",20.2961,85.8245),
        ("Dehradun",30.3165,78.0322),("Ranchi",23.3441,85.3096),
        ("Mysore",12.2958,76.6394),("Jodhpur",26.2389,73.0243),
    ],
    "China": [
        ("Beijing",39.9042,116.4074),("Shanghai",31.2304,121.4737),
        ("Guangzhou",23.1291,113.2644),("Chengdu",30.5728,104.0668),
        ("Wuhan",30.5928,114.3055),("Xi'an",34.3416,108.9398),
        ("Shenzhen",22.5431,114.0579),("Hangzhou",30.2741,120.1551),
        ("Nanjing",32.0603,118.7969),("Tianjin",39.3434,117.3616),
        ("Chongqing",29.5630,106.5516),("Harbin",45.8038,126.5349),
        ("Zhengzhou",34.7466,113.6254),("Qingdao",36.0671,120.3826),
        ("Kunming",25.0453,102.7097),("Urumqi",43.8256,87.6168),
        ("Lhasa",29.6500,91.1000),("Shenyang",41.8057,123.4315),
        ("Jinan",36.6512,117.1200),("Fuzhou",26.0745,119.2965),
        ("Xiamen",24.4798,118.0894),("Nanning",22.8170,108.3665),
    ],
    "Japan": [
        ("Tokyo",35.6762,139.6503),("Osaka",34.6937,135.5023),
        ("Kyoto",35.0116,135.7681),("Hiroshima",34.3853,132.4553),
        ("Sapporo",43.0618,141.3545),("Nagoya",35.1815,136.9066),
        ("Kobe",34.6913,135.1830),("Fukuoka",33.5904,130.4017),
        ("Sendai",38.2682,140.8694),("Yokohama",35.4437,139.6380),
        ("Kawasaki",35.5308,139.7030),("Naha",26.2124,127.6809),
        ("Kanazawa",36.5944,136.6256),("Kumamoto",32.8031,130.7079),
        ("Kagoshima",31.5969,130.5571),
    ],
    "United States": [
        ("New York",40.7128,-74.0060),("Los Angeles",34.0522,-118.2437),
        ("Chicago",41.8781,-87.6298),("Houston",29.7604,-95.3698),
        ("Phoenix",33.4484,-112.0740),("Philadelphia",39.9526,-75.1652),
        ("San Antonio",29.4241,-98.4936),("San Diego",32.7157,-117.1611),
        ("Dallas",32.7767,-96.7970),("San Jose",37.3382,-121.8863),
        ("Washington DC",38.9072,-77.0369),("Seattle",47.6062,-122.3321),
        ("Boston",42.3601,-71.0589),("Miami",25.7617,-80.1918),
        ("Atlanta",33.7490,-84.3880),("Denver",39.7392,-104.9903),
        ("Las Vegas",36.1699,-115.1398),("Minneapolis",44.9778,-93.2650),
        ("Portland",45.5051,-122.6750),("Honolulu",21.3069,-157.8583),
    ],
    "United Kingdom": [
        ("London",51.5074,-0.1278),("Manchester",53.4808,-2.2426),
        ("Birmingham",52.4862,-1.8904),("Edinburgh",55.9533,-3.1883),
        ("Glasgow",55.8642,-4.2518),("Liverpool",53.4084,-2.9916),
        ("Leeds",53.8008,-1.5491),("Sheffield",53.3811,-1.4701),
        ("Bristol",51.4545,-2.5879),("Cardiff",51.4816,-3.1791),
        ("Belfast",54.5973,-5.9301),("Newcastle",54.9783,-1.6178),
        ("Nottingham",52.9548,-1.1581),("Leicester",52.6369,-1.1398),
        ("Cambridge",52.2053,0.1218),
    ],
    "Germany": [
        ("Berlin",52.5200,13.4050),("Munich",48.1351,11.5820),
        ("Frankfurt",50.1109,8.6821),("Hamburg",53.5753,10.0153),
        ("Cologne",50.9333,6.9500),("Stuttgart",48.7758,9.1829),
        ("Düsseldorf",51.2217,6.7762),("Dortmund",51.5136,7.4653),
        ("Bremen",53.0793,8.8017),("Hannover",52.3759,9.7320),
        ("Leipzig",51.3397,12.3731),("Dresden",51.0504,13.7373),
        ("Nuremberg",49.4521,11.0767),("Bochum",51.4818,7.2162),
        ("Wuppertal",51.2562,7.1508),
    ],
    "France": [
        ("Paris",48.8566,2.3522),("Lyon",45.7640,4.8357),
        ("Marseille",43.2965,5.3698),("Toulouse",43.6047,1.4442),
        ("Nice",43.7102,7.2620),("Nantes",47.2184,-1.5536),
        ("Montpellier",43.6110,3.8767),("Strasbourg",48.5734,7.7521),
        ("Bordeaux",44.8378,-0.5792),("Lille",50.6292,3.0573),
        ("Rennes",48.1173,-1.6778),("Grenoble",45.1885,5.7245),
    ],
    "Pakistan": [
        ("Karachi",24.8607,67.0011),("Lahore",31.5497,74.3436),
        ("Islamabad",33.6844,73.0479),("Rawalpindi",33.6007,73.0679),
        ("Faisalabad",31.4504,73.1350),("Multan",30.1575,71.5249),
        ("Peshawar",34.0150,71.5805),("Quetta",30.1798,66.9750),
        ("Hyderabad",25.3960,68.3578),("Gujranwala",32.1877,74.1945),
        ("Sialkot",32.4945,74.5229),("Bahawalpur",29.3956,71.6836),
    ],
    "Bangladesh": [
        ("Dhaka",23.8103,90.4125),("Chittagong",22.3569,91.7832),
        ("Sylhet",24.8949,91.8687),("Rajshahi",24.3745,88.6042),
        ("Khulna",22.8456,89.5403),("Barisal",22.7010,90.3535),
        ("Mymensingh",24.7471,90.4203),("Comilla",23.4607,91.1809),
        ("Rangpur",25.7439,89.2752),("Narayanganj",23.6238,90.4996),
    ],
    "Indonesia": [
        ("Jakarta",-6.2088,106.8456),("Surabaya",-7.2575,112.7521),
        ("Bandung",-6.9175,107.6191),("Medan",-3.5952,98.6722),
        ("Semarang",-6.9932,110.4203),("Palembang",-2.9761,104.7754),
        ("Makassar",-5.1477,119.4327),("Denpasar",-8.6705,115.2126),
        ("Yogyakarta",-7.7956,110.3695),("Manado",1.4748,124.8421),
        ("Balikpapan",-1.2675,116.8289),("Samarinda",-0.5022,117.1536),
        ("Pontianak",-0.0263,109.3425),("Padang",-0.9471,100.4172),
    ],
    "Australia": [
        ("Sydney",-33.8688,151.2093),("Melbourne",-37.8136,144.9631),
        ("Brisbane",-27.4698,153.0251),("Perth",-31.9505,115.8605),
        ("Adelaide",-34.9285,138.6007),("Canberra",-35.2809,149.1300),
        ("Gold Coast",-28.0167,153.4000),("Newcastle",-32.9283,151.7817),
        ("Wollongong",-34.4278,150.8931),("Hobart",-42.8821,147.3272),
        ("Darwin",-12.4634,130.8456),("Cairns",-16.9186,145.7781),
    ],
    "Russia": [
        ("Moscow",55.7558,37.6173),("Saint Petersburg",59.9311,30.3609),
        ("Novosibirsk",54.9833,82.8964),("Yekaterinburg",56.8389,60.6057),
        ("Kazan",55.7887,49.1221),("Chelyabinsk",55.1644,61.4368),
        ("Omsk",54.9885,73.3242),("Samara",53.2001,50.1500),
        ("Rostov-on-Don",47.2357,39.7015),("Ufa",54.7388,55.9721),
        ("Vladivostok",43.1155,131.8855),("Sochi",43.6028,39.7342),
    ],
    "Brazil": [
        ("São Paulo",-23.5505,-46.6333),("Rio de Janeiro",-22.9068,-43.1729),
        ("Brasília",-15.7942,-47.8822),("Salvador",-12.9714,-38.5014),
        ("Fortaleza",-3.7172,-38.5437),("Belo Horizonte",-19.9167,-43.9345),
        ("Manaus",-3.1019,-60.0250),("Curitiba",-25.4284,-49.2733),
        ("Recife",-8.0578,-34.8829),("Porto Alegre",-30.0346,-51.2177),
        ("Belém",-1.4558,-48.5044),("Goiânia",-16.6864,-49.2643),
    ],
    "South Korea": [
        ("Seoul",37.5665,126.9780),("Busan",35.1796,129.0756),
        ("Incheon",37.4563,126.7052),("Daegu",35.8714,128.6014),
        ("Daejeon",36.3504,127.3845),("Gwangju",35.1595,126.8526),
        ("Suwon",37.2636,127.0286),("Ulsan",35.5384,129.3114),
        ("Changwon",35.2281,128.6811),("Jeju",33.4996,126.5312),
    ],
    "United Arab Emirates": [
        ("Dubai",25.2048,55.2708),("Abu Dhabi",24.4539,54.3773),
        ("Sharjah",25.3463,55.4209),("Al Ain",24.2075,55.7447),
        ("Ajman",25.4111,55.4354),("Ras Al Khaimah",25.7895,55.9432),
        ("Fujairah",25.1288,56.3265),
    ],
    "Turkey": [
        ("Istanbul",41.0082,28.9784),("Ankara",39.9334,32.8597),
        ("Izmir",38.4192,27.1287),("Bursa",40.1826,29.0665),
        ("Adana",37.0000,35.3213),("Gaziantep",37.0662,37.3833),
        ("Konya",37.8713,32.4846),("Antalya",36.8969,30.7133),
        ("Trabzon",41.0027,39.7168),("Mersin",36.7921,34.6210),
    ],
    "Iran": [
        ("Tehran",35.6892,51.3890),("Mashhad",36.2605,59.6168),
        ("Isfahan",32.6539,51.6660),("Tabriz",38.0800,46.2919),
        ("Shiraz",29.5918,52.5836),("Ahvaz",31.3203,48.6692),
        ("Qom",34.6401,50.8764),("Kermanshah",34.3277,47.0786),
    ],
    "Israel": [
        ("Tel Aviv",32.0853,34.7818),("Jerusalem",31.7683,35.2137),
        ("Haifa",32.7940,34.9896),("Beer Sheva",31.2518,34.7913),
        ("Netanya",32.3321,34.8565),("Ashdod",31.8044,34.6553),
    ],
    "Ukraine": [
        ("Kyiv",50.4501,30.5234),("Kharkiv",49.9935,36.2304),
        ("Odessa",46.4774,30.7326),("Dnipro",48.4647,35.0462),
        ("Donetsk",48.0159,37.8028),("Lviv",49.8397,24.0297),
        ("Zaporizhzhia",47.8388,35.1396),("Mykolaiv",46.9750,31.9946),
    ],
    "Saudi Arabia": [
        ("Riyadh",24.7136,46.6753),("Jeddah",21.4858,39.1925),
        ("Mecca",21.3891,39.8579),("Medina",24.5247,39.5692),
        ("Dammam",26.4207,50.0888),("Khobar",26.2172,50.1971),
        ("Tabuk",28.3835,36.5662),("Abha",18.2164,42.5053),
    ],
    "Egypt": [
        ("Cairo",30.0444,31.2357),("Alexandria",31.2001,29.9187),
        ("Giza",30.0131,31.2089),("Luxor",25.6872,32.6396),
        ("Aswan",24.0889,32.8998),("Hurghada",27.2574,33.8129),
        ("Port Said",31.2565,32.2841),("Suez",29.9668,32.5498),
    ],
    "South Africa": [
        ("Johannesburg",-26.2041,28.0473),("Cape Town",-33.9249,18.4241),
        ("Durban",-29.8587,31.0218),("Pretoria",-25.7479,28.2293),
        ("Port Elizabeth",-33.9608,25.6022),("Bloemfontein",-29.0852,26.1596),
        ("East London",-33.0153,27.9116),
    ],
    "Nigeria": [
        ("Lagos",6.5244,3.3792),("Abuja",9.0765,7.3986),
        ("Kano",12.0022,8.5920),("Ibadan",7.3775,3.9470),
        ("Port Harcourt",4.8156,7.0498),("Benin City",6.3350,5.6037),
        ("Enugu",6.4584,7.5464),("Kaduna",10.5105,7.4165),
    ],
    "Kenya": [
        ("Nairobi",-1.2921,36.8219),("Mombasa",-4.0435,39.6682),
        ("Kisumu",-0.0917,34.7680),("Nakuru",-0.3031,36.0800),
        ("Eldoret",0.5143,35.2698),
    ],
    "Mexico": [
        ("Mexico City",19.4326,-99.1332),("Guadalajara",20.6597,-103.3496),
        ("Monterrey",25.6866,-100.3161),("Cancún",21.1619,-86.8515),
        ("Tijuana",32.5149,-117.0382),("Puebla",19.0414,-98.2063),
        ("León",21.1221,-101.6872),("Mérida",20.9674,-89.5926),
    ],
    "Argentina": [
        ("Buenos Aires",-34.6037,-58.3816),("Córdoba",-31.4135,-64.1811),
        ("Rosario",-32.9468,-60.6393),("Mendoza",-32.8908,-68.8272),
        ("La Plata",-34.9215,-57.9545),("San Miguel de Tucumán",-26.8083,-65.2176),
    ],
    "Canada": [
        ("Toronto",43.6532,-79.3832),("Vancouver",49.2827,-123.1207),
        ("Montreal",45.5017,-73.5673),("Calgary",51.0447,-114.0719),
        ("Edmonton",53.5461,-113.4938),("Ottawa",45.4215,-75.6972),
        ("Winnipeg",49.8951,-97.1384),("Quebec City",46.8139,-71.2080),
        ("Halifax",44.6488,-63.5752),("Victoria",48.4284,-123.3656),
    ],
    "Italy": [
        ("Rome",41.9028,12.4964),("Milan",45.4654,9.1859),
        ("Naples",40.8518,14.2681),("Turin",45.0703,7.6869),
        ("Palermo",38.1157,13.3615),("Genoa",44.4056,8.9463),
        ("Bologna",44.4949,11.3426),("Florence",43.7696,11.2558),
        ("Venice",45.4408,12.3155),("Bari",41.1171,16.8719),
    ],
    "Spain": [
        ("Madrid",40.4168,-3.7038),("Barcelona",41.3851,2.1734),
        ("Valencia",39.4699,-0.3763),("Seville",37.3891,-5.9845),
        ("Zaragoza",41.6488,-0.8891),("Málaga",36.7213,-4.4214),
        ("Bilbao",43.2630,-2.9350),("Alicante",38.3452,-0.4815),
        ("Las Palmas",28.1235,-15.4363),
    ],
    "Thailand": [
        ("Bangkok",13.7563,100.5018),("Chiang Mai",18.7883,98.9853),
        ("Pattaya",12.9236,100.8825),("Phuket",7.8804,98.3923),
        ("Khon Kaen",16.4322,102.8236),("Hat Yai",7.0080,100.4747),
        ("Nakhon Ratchasima",14.9799,102.0978),
    ],
    "Vietnam": [
        ("Ho Chi Minh City",10.8231,106.6297),("Hanoi",21.0285,105.8542),
        ("Da Nang",16.0544,108.2022),("Hai Phong",20.8449,106.6881),
        ("Can Tho",10.0452,105.7469),("Hue",16.4637,107.5909),
    ],
    "Philippines": [
        ("Manila",14.5995,120.9842),("Quezon City",14.6760,121.0437),
        ("Davao",7.1907,125.4553),("Cebu City",10.3157,123.8854),
        ("Zamboanga",6.9214,122.0790),("Cagayan de Oro",8.4542,124.6319),
    ],
    "Malaysia": [
        ("Kuala Lumpur",3.1390,101.6869),("George Town",5.4141,100.3288),
        ("Johor Bahru",1.4927,103.7414),("Ipoh",4.5975,101.0901),
        ("Shah Alam",3.0738,101.5183),("Petaling Jaya",3.1073,101.6067),
        ("Kota Kinabalu",5.9788,116.0753),("Kuching",1.5497,110.3592),
    ],
    "Singapore": [
        ("Singapore",1.3521,103.8198),("Jurong",1.3329,103.7436),
        ("Tampines",1.3521,103.9449),("Woodlands",1.4370,103.7868),
    ],
    "New Zealand": [
        ("Auckland",-36.8485,174.7633),("Wellington",-41.2866,174.7756),
        ("Christchurch",-43.5321,172.6362),("Hamilton",-37.7870,175.2793),
        ("Dunedin",-45.8788,170.5028),("Tauranga",-37.6878,176.1651),
    ],
    "Sweden": [
        ("Stockholm",59.3293,18.0686),("Gothenburg",57.7089,11.9746),
        ("Malmö",55.6050,13.0038),("Uppsala",59.8586,17.6389),
        ("Linköping",58.4108,15.6214),
    ],
    "Norway": [
        ("Oslo",59.9139,10.7522),("Bergen",60.3913,5.3221),
        ("Trondheim",63.4305,10.3951),("Stavanger",58.9700,5.7331),
        ("Tromsø",69.6496,18.9560),
    ],
    "Netherlands": [
        ("Amsterdam",52.3676,4.9041),("Rotterdam",51.9244,4.4777),
        ("The Hague",52.0705,4.3007),("Utrecht",52.0907,5.1214),
        ("Eindhoven",51.4416,5.4697),("Groningen",53.2194,6.5665),
    ],
    "Poland": [
        ("Warsaw",52.2297,21.0122),("Kraków",50.0647,19.9450),
        ("Gdańsk",54.3520,18.6466),("Wrocław",51.1079,17.0385),
        ("Poznań",52.4064,16.9252),("Łódź",51.7592,19.4560),
    ],
    "Greece": [
        ("Athens",37.9838,23.7275),("Thessaloniki",40.6401,22.9444),
        ("Patras",38.2466,21.7346),("Heraklion",35.3387,25.1442),
        ("Rhodes",36.4341,28.2176),
    ],
    "Portugal": [
        ("Lisbon",38.7223,-9.1393),("Porto",41.1579,-8.6291),
        ("Braga",41.5454,-8.4265),("Coimbra",40.2033,-8.4103),
        ("Faro",37.0194,-7.9322),
    ],
    "Switzerland": [
        ("Zurich",47.3769,8.5417),("Geneva",46.2044,6.1432),
        ("Basel",47.5596,7.5886),("Bern",46.9480,7.4474),
        ("Lausanne",46.5197,6.6323),
    ],
    "Austria": [
        ("Vienna",48.2082,16.3738),("Graz",47.0707,15.4395),
        ("Linz",48.3069,14.2858),("Salzburg",47.8095,13.0550),
        ("Innsbruck",47.2692,11.4041),
    ],
    "Belgium": [
        ("Brussels",50.8503,4.3517),("Antwerp",51.2194,4.4025),
        ("Ghent",51.0543,3.7174),("Bruges",51.2093,3.2247),
        ("Liège",50.6325,5.5797),
    ],
    "Czech Republic": [
        ("Prague",50.0755,14.4378),("Brno",49.1951,16.6068),
        ("Ostrava",49.8209,18.2625),("Plzeň",49.7477,13.3776),
    ],
    "Hungary": [
        ("Budapest",47.4979,19.0402),("Debrecen",47.5316,21.6273),
        ("Miskolc",48.1035,20.7784),("Győr",47.6875,17.6504),
    ],
    "Romania": [
        ("Bucharest",44.4268,26.1025),("Cluj-Napoca",46.7712,23.6236),
        ("Timișoara",45.7489,21.2087),("Iași",47.1585,27.6014),
    ],
    "Iraq": [
        ("Baghdad",33.3152,44.3661),("Basra",30.5085,47.7804),
        ("Mosul",36.3350,43.1189),("Erbil",36.1901,44.0091),
        ("Kirkuk",35.4681,44.3922),
    ],
    "Afghanistan": [
        ("Kabul",34.5553,69.2075),("Kandahar",31.6289,65.7372),
        ("Herat",34.3482,62.2040),("Mazar-i-Sharif",36.7069,67.1147),
    ],
    "Ethiopia": [
        ("Addis Ababa",8.9806,38.7578),("Dire Dawa",9.5931,41.8661),
        ("Mekelle",13.4967,39.4753),("Gondar",12.6090,37.4680),
    ],
    "Ghana": [
        ("Accra",5.6037,-0.1870),("Kumasi",6.6885,-1.6244),
        ("Tamale",9.4008,-0.8393),("Takoradi",4.8845,-1.7554),
    ],
}

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCATION_ALIASES = {"Russian Federation": "Russia", "Viet Nam": "Vietnam"}

_FALLBACK_CITIES_BY_ISO = {}
_CAPITAL_THREAD_STARTED = False


def _ensure_fallback_capitals():
    """Fill _FALLBACK_CITIES_BY_ISO with each country's capital (background fetch, REST Countries — free)."""
    global _CAPITAL_THREAD_STARTED
    if _CAPITAL_THREAD_STARTED:
        return
    _CAPITAL_THREAD_STARTED = True

    def _run():
        global _FALLBACK_CITIES_BY_ISO
        try:
            u = "https://restcountries.com/v3.1/all?fields=cca2,capital,capitalInfo,latlng"
            with urllib.request.urlopen(u, timeout=45) as r:
                data = json.loads(r.read())
            out = {}
            for c in data:
                iso = c.get("cca2")
                if not iso:
                    continue
                caps = c.get("capital") or []
                ci = c.get("capitalInfo") or {}
                ll = ci.get("latlng")
                if (not ll or len(ll) < 2) and c.get("latlng"):
                    ll = c["latlng"]
                if caps and ll and len(ll) >= 2:
                    try:
                        out[iso] = [(caps[0], float(ll[0]), float(ll[1]))]
                    except (TypeError, ValueError, IndexError):
                        pass
            _FALLBACK_CITIES_BY_ISO = out
        except Exception:
            _FALLBACK_CITIES_BY_ISO = {}

    threading.Thread(target=_run, daemon=True).start()


def _country_rows():
    path = os.path.join(_BASE_DIR, "weather_countries.json")
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and len(data) >= 100:
                return sorted(data, key=lambda x: x["name"].lower())
        except Exception:
            pass
    try:
        from gen_countries import pairs as _ps

        return sorted([{"code": a, "name": b} for a, b in _ps], key=lambda x: x["name"].lower())
    except Exception:
        return [{"code": "NP", "name": "Nepal"}, {"code": "IN", "name": "India"}]


_ROWS = _country_rows()
COUNTRY_NAMES = [r["name"] for r in _ROWS]
ISO_BY_NAME = {r["name"]: r["code"] for r in _ROWS}


def location_key_for_country(display_name):
    return LOCATION_ALIASES.get(display_name, display_name)


def cities_for(display_name):
    key = location_key_for_country(display_name)
    manual = LOCATIONS.get(key)
    if manual:
        return list(manual)
    iso = ISO_BY_NAME.get(display_name)
    if not iso:
        return []
    _ensure_fallback_capitals()
    got = _FALLBACK_CITIES_BY_ISO.get(iso)
    if got:
        return list(got)
    return []


def country_iso(display_name):
    return ISO_BY_NAME.get(display_name)


def geocode_search(country_iso_code, query, callback):
    """Open-Meteo Geocoding API — no API key."""

    def _run():
        q = query.strip()
        if not q or not country_iso_code:
            callback([])
            return
        try:
            u = (
                "https://geocoding-api.open-meteo.com/v1/search?"
                + urllib.parse.urlencode(
                    {
                        "name": q,
                        "count": 12,
                        "language": "en",
                        "format": "json",
                        "countryCode": country_iso_code,
                    }
                )
            )
            with urllib.request.urlopen(u, timeout=12) as r:
                d = json.loads(r.read())
            results = d.get("results") or []
            out = []
            for it in results:
                lat, lon = it.get("latitude"), it.get("longitude")
                if lat is None or lon is None:
                    continue
                nm = it.get("name") or ""
                adm = (it.get("admin1") or "")[:22]
                label = f"{nm} ({adm})" if adm else nm
                out.append({"name": nm, "label": label, "lat": float(lat), "lon": float(lon)})
            callback(out)
        except Exception:
            callback([])

    threading.Thread(target=_run, daemon=True).start()


def fetch_weather(city, lat, lon, callback):
    def _run():
        try:
            url = (f"https://api.open-meteo.com/v1/forecast?"
                   f"latitude={lat}&longitude={lon}"
                   f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,"
                   f"weather_code,apparent_temperature,precipitation"
                   f"&daily=temperature_2m_max,temperature_2m_min,weather_code,precipitation_sum"
                   f"&timezone=auto&forecast_days=5")
            with urllib.request.urlopen(url, timeout=10) as r:
                d = json.loads(r.read())
            cur = d["current"]; daily = d.get("daily",{})
            result = {
                "city":     city,
                "temp":     cur["temperature_2m"],
                "feels":    cur["apparent_temperature"],
                "humidity": cur["relative_humidity_2m"],
                "wind":     cur["wind_speed_10m"],
                "precip":   cur.get("precipitation",0),
                "desc":     WMO.get(cur["weather_code"],"Unknown"),
                "code":     cur["weather_code"],
                "forecast": [],
            }
            for i in range(min(5, len(daily.get("time",[])))):
                result["forecast"].append({
                    "date":   daily["time"][i],
                    "max":    daily.get("temperature_2m_max",[None]*10)[i],
                    "min":    daily.get("temperature_2m_min",[None]*10)[i],
                    "desc":   WMO.get((daily.get("weather_code",[0]*10)[i]),""),
                    "rain":   daily.get("precipitation_sum",[0]*10)[i],
                })
            callback(result)
        except Exception as e:
            callback({"error":str(e),"city":city})
    threading.Thread(target=_run, daemon=True).start()