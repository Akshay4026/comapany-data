from fastapi import FastAPI, Query
import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv
from s3Utility import upload_file, read_file_from_s3, download_file_from_s3
from enriching import query_perplexity

load_dotenv()

app = FastAPI()


# ------------------- Extraction -------------------
@app.get("/companies/{state}")
def get_companies(state :str):
    url = "https://api.data.gov.in/resource/4dbe5667-7b6b-41d7-82af-211562424d9a"
    company_API = os.getenv("COMPANIES_API_KEY")

    params = {
        "api-key": company_API,
        "format": "json",
        "filters[CompanyStateCode]": state,  ## we can only extract state list using this govt registry api ,so we can add filters state wise later in processing phase
        "limit": 100
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        folder_name = "unprocessedList"

        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        local_path = f"{folder_name}/companies_telangana_hyd_{timestamp}.json"

        with open(local_path, "w") as f:
            json.dump(data, f)

        print(f"Uploading file {local_path} to S3...")
        s3_key = f"{folder_name}/{os.path.basename(local_path)}"
        upload_file(local_path, s3_key)
        print("Upload finished")

        return {"message": "Data fetched and saved to S3", "s3_file": s3_key}
    else:
        return {"error": response.text}


# ------------------- Transformation -------------------
@app.get("/processing/{path:path}") ## need to work more on this cause that govt regsitry data set is very messy found as many issues as possible have to recheck once
def processingJson(path :str):
    LOCAL_FOLDER = "processedList"
    # path ="unprocessedList/companies_telangana_hyd_20250904004453.json"

    if not os.path.exists(LOCAL_FOLDER):
        os.makedirs(LOCAL_FOLDER)

    file_content = read_file_from_s3(path)
    data = json.loads(file_content)

    print(f"Processing {len(data.get('records', []))} companies...")

    cleaned_dict = {}
    IT_CIN_PREFIXES = ("U72200", "U72300", "U72400", "U72900", "U62099", "U62091", "L72200")
    IT_KEYWORDS = [
        "TECHNOLOGY", "INFORMATION TECHNOLOGY",
        "SYSTEMS",
        "SOFTWARE", "AI", "PLATFORM", "ANALYTICS"
    ]
    TARGET_CATEGORY = "BUSINESS SERVICES"
    for company in data.get("records", []):
        cin = company.get("CIN", "").strip().upper()
        name = company.get("CompanyName", "").strip().upper()
        category = company.get("CompanyCategory", "").strip().upper()
        if category == TARGET_CATEGORY and cin.startswith(IT_CIN_PREFIXES) or any(word in name for word in IT_KEYWORDS):
            cleaned_dict[cin] = {
                "CIN": cin,
                "CompanyName": company.get("CompanyName", "").strip(),
                "CompanyROCcode": company.get("CompanyROCcode", "").strip(),
                "CompanyCategory": company.get("CompanyCategory", "").strip(),
                "CompanyRegistrationdate_date": company.get("CompanyRegistrationdate_date", "").strip(),
                "CompanyStatus": company.get("CompanyStatus", "").strip(),
                "CompanyStateCode": company.get("CompanyStateCode", "").strip(),
                "CompanyIndustrialClassification": company.get("CompanyIndustrialClassification", "").strip()
            }

    cleaned_data = list(cleaned_dict.values())

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    clean_file = f"{LOCAL_FOLDER}/clean_it_companies_{timestamp}.json"

    with open(clean_file, "w") as f:
        json.dump(cleaned_data, f, indent=2)

    s3_key = f"processed/{os.path.basename(clean_file)}"
    upload_file(clean_file, s3_key)

    return {
        "message": f"Cleaned IT-related companies data saved and uploaded",
        "s3_file": s3_key,
        "records_count": len(cleaned_data)
    }


# ------------------- Enrichment -------------------
@app.get("/enriching/{path:path}")
def enrichingJson(path: str):
    LOCAL_FOLDER = "enrichedList"
    if not os.path.exists(LOCAL_FOLDER):
        os.makedirs(LOCAL_FOLDER)

    file_content = read_file_from_s3(path)
    data = json.loads(file_content)

    sample_records = data[:5]  # exhauting my api credits so working on 5 for now
    print(f"Enriching {len(sample_records)} companies...")

    service_categories_map = {
        "Software Development": ["software", "app", "development", "saas"],
        "Cloud Services": ["cloud", "aws", "azure", "gcp", "server"],
        "Consulting / Service": ["consulting", "service", "advisory","IT"],
        "Product-Based": ["product", "platform", "solution"]
    }

    def categorize_services(services_list):
        categories = set()
        for s in services_list:
            s_lower = s.lower()
            matched = False
            for cat, keywords in service_categories_map.items():
                if any(k in s_lower for k in keywords):
                    categories.add(cat)
                    matched = True
            if not matched:
                categories.add("Other / Misc")
        return list(categories)

    enriched_data = []
    for company in sample_records:
        top_directors = company.get("top_directors", [])

        extra = query_perplexity(company)
        if extra:
            company.update(extra)

        services = company.get("services_provided", [])
        company["service_categories"] = categorize_services(services)

        company["top_directors"] = top_directors # Was thinking to remove this to save tokens .

        enriched_data.append(company)

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    enriched_file = f"{LOCAL_FOLDER}/enriched_business_services_{timestamp}.json"
    with open(enriched_file, "w") as f:
        json.dump(enriched_data, f, indent=2)

    s3_key = f"enrichedList/{os.path.basename(enriched_file)}"
    upload_file(enriched_file, s3_key)

    return {
        "message": "Business Services data enriched with Perplexity saved and uploaded",
        "s3_file": s3_key,
        "records_count": len(enriched_data)
    }

# ------------------- Scoring -------------------
@app.get("/score/{path:path}")
def score_companies_route(path: str, target_categories: str = "Software Development,Cloud Services,service"):#considered these two for now later we can add few more in the flow
    LOCAL_FOLDER = "scoredList"
    if not os.path.exists(LOCAL_FOLDER):
        os.makedirs(LOCAL_FOLDER)

    target_categories = [cat.strip() for cat in target_categories.split(",")]

    file_content = read_file_from_s3(path)
    companies = json.loads(file_content)

    size_map = {"Small": 1, "Medium": 2, "Large": 3}

    for company in companies:
        ld_score = 1 if company.get("L&D_active") else 0
        size_score = size_map.get(company.get("size", "Small"), 1) / 3
        service_categories = company.get("service_categories", [])
        service_score = len(set(service_categories) & set(target_categories)) / len(target_categories)
        total_score = (ld_score * 0.4) + (size_score * 0.35) + (service_score * 0.25)
        company["score"] = round(total_score, 2) # temp scoring tecchnique we can add few more after enriching 

    sorted_companies = sorted(companies, key=lambda x: x["score"], reverse=True)

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    scored_file = f"{LOCAL_FOLDER}/scored_companies_{timestamp}.json"
    with open(scored_file, "w") as f:
        json.dump(sorted_companies, f, indent=2)

    s3_key = f"scoredList/{os.path.basename(scored_file)}"
    upload_file(scored_file, s3_key)

    return {
        "message": "Companies scored and uploaded successfully",
        "s3_file": s3_key,
        "records_count": len(sorted_companies),
        "top_5_companies": sorted_companies[:5]
    }




