from flask import Flask, request, jsonify, send_file
import os
import requests
import sqlite3
from dotenv import load_dotenv
from openai import OpenAI
import time
from PIL import Image


# Load environment variables from .env file
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Set up OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

# Define the table name
table_name = "medical_info"

# Function to execute a query and return detailed execution steps (for textual queries)
def execute_query_with_steps(query):
    steps = []
    try:
        conn = sqlite3.connect('medical.db')
        steps.append("Connected to the database 'medical.db'.")
        
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
        table_exists = cursor.fetchone()
        if table_exists:
            steps.append(f"Table '{table_name}' exists.")
        else:
            steps.append(f"Table '{table_name}' does not exist.")
            return {"error": f"Table '{table_name}' does not exist.", "steps": steps}

        cursor.execute(query)
        result = cursor.fetchall()
        steps.append(f"Query executed: {query}")
        
        steps.append(f"Fetched {len(result)} rows.")
        conn.close()
        steps.append("Database connection closed.")
        
        return {"result": result, "steps": steps}
    
    except sqlite3.Error as e:
        steps.append(f"SQLite error occurred: {str(e)}")
        return {"error": str(e), "steps": steps}
    
    except Exception as e:
        steps.append(f"An error occurred: {str(e)}")
        return {"error": str(e), "steps": steps}

# Function to convert a question to an SQL query using OpenAI (for textual queries)
# Function to convert question to SQL query using OpenAI
def question_to_sql(question):
    column_descriptions = {
       "CASE_ID":'case id of the patient',
        "AGE":'age of the patient.',
        "SEX":'biological sex at birth',
        "RACE1_AIAN":'American Indian or Alaska Native',
        "RACE1_AS":'race is Asian',
        "RACE1_BL":'race is Black or African American',
        "RACE1_NH":'race is Native Hawaiian or Pacific Islander',
        "RACE1_WH":'race is White',
        "RACE1_OT":'Whether patient belong to other races or not- yes or no',
        "RACE1_OT_TXT":'If race is Other the what is that race is mentioned',
        "RACE2_AI":'race is Asian Indian',
        "RACE2_CH":'race is Chinese',
        "RACE2_FI":'race is Filipino',
        "RACE2_JA":'race is Japanese',
        "RACE2_KO":' race is Korean',
        "RACE2_VI":' race is Vietnamese',
        "RACE2_OT":'Whether patient belong to other races or not- yes or no',
        "RACE2_TXT":'If race is Other the what is that race is mentioned',
        "RACE3_AFRICAN":'race is African',
       "RACE3_AMBIRTH":'race is African American of American origin (born in America)',
       "RACE3_AFBIRTH":'race is African American of African origin (born in Africa)',
       "RACE3_CABIRTH":'race is African American of Caribbean origin (born in one of the Caribbean Islands)',
       "RACE3_CA":'race is Caribbean',
       "RACE3_OT":'Whether patient belong to other races or not- yes or no',
       "RACE3_OT_TXT":'If race is Other the what is that race is mentioned',
       "HLS_YN":'Are you of Hispanic, Latina, or Spanish origin',
       "HLS_LA":'is a Hispanic, Latina, or Spanish origin and is a Latin American',
       "HLS_ME":'is a Hispanic, Latina, or Spanish origin and is a (Mexican,Mexican American,or Chicana)',
       "HLS_PR":'is a Hispanic, Latina, or Spanish origin and is a Puerto Rican ',
       "HLS_OT":' Other Hispanic, Latina, or Spanish origin (e g , Salvadoran, Dominican, Colombian, Guatemalan, Spaniard, Ecuadorian, etc )',
       "HLS_OT_TXT":'Other Hispanic, Latina, or Spanish origin (e g , Salvadoran, Dominican, Colombian, Guatemalan, Spaniard, Ecuadorian, etc ) and what is that origin ',
       "C_AIDS":'patient has Acquired immune-deficiency syndrome (AIDS)',
       "C_AR":'patient has Arthritis or other rheumatic diseases',
       "C_CN":'patient has Cancer or not yes or no',
       "C_CN_FOLLOWON1":'has cancer, does the patient have a tumor? yes or no',
       "C_CN_FOLLOWON3":'has cancer,is it leukemia? yes or no',
       "C_CN_FOLLOWON2":'has cancer, is it lymphoma? yes or no',
       "C_CVA":'Cerebral vascular accident (stroke) or transient ischemic attack (TIA) yes or no',
       "C_CKD":' has Chronic kidney disease (CKD) yes or no',
       "C_CKD_FOLLOWON":'has Chronic kidney disease (CKD) and status is mild, moderate, Severe (on dialysis, status post kidney transplant, uremia) any one of these',
       "C_COPD":'has Chronic lung disease (COPD) yes or no',
       "C_CTD":' has Connective tissue disease yes or no',
       "C_CHF":'has Congestive heart failure (CHF) yes or no',
       "C_DM":' has Dementia yes or no',
       "C_DB":' has Diabetes yes or no ',
       "C_DB_FOLLOWON":'status of Diabetes - Diet controlled,Uncomplicated (No end-organ damage, such as peripheral neuropathy, nephropathy and/or PAD),Complicated (End-organ damage, such as peripheral neuropathy, nephropathy and/or PAD)',
       "C_HYPERLIPID":'has Hyperlipidemia (high cholesterol) yes or no',
       "C_HYPERTEN":'has Hypertension (high blood pressure) yes or no',
       "C_LD":'has Liver disease yes or no',
       "C_LD_FOLLOWON":'has liver disease where status is Mild,Moderate to severe',
       "C_HA":' has Myocardial infarction (heart attack) yes or no ',
       "C_HP":'has Paralysis of one side of the body (hemiplegia) yes or no',
       "C_PVD":'has Peripheral vascular disease yes or no',
       "C_PUD":' has Peptic ulcer disease yes or no',
       "C_NONE":'None of these yes or no',
       "INS_YN":'currently have health insurance yes or no',
       "INS_TYPE_EMP":'health insurance through a current or former employer-yes or no',
       "INS_TYPE_OT_EMP":'health insurance through someone else employer (e g , your spouse, partner, or parents) yes or no',
       "INS_TYPE_PLAN":' has Individual/family insurance plans yes or no',
       "INS_TYPE_MEDICAID":'has Medicaid (MediCal for California residents) yes or no',
       "INS_TYPE_VET":' has or under health insurance called Veterans administration (VA)/CHAMPUS yes or no',
       "INS_TYPE_TRI":' health insurance  is TRICARE yes or no',
       "INS_TYPE_MEDICARE":' health insurance is Medicare yes or no',
       "INS_TYPE_NS":'health insurance Not sure yes or no',
       "INS_TYPE_OT":'Other  health insurance type yes or no',
       "INS_TYPE_OT_TXT":'has Other health insurance type and that is mentioned',
       "INS_RX_COST":'Has the cost of prescription medication ever prevented you from taking a prescription medication yes or no or other',
       "INS_RX_COST_TXT":'Has the cost of prescription medication ever prevented you from taking a prescription medication if other then the reason is mentioned',
       "PCP_YN":'Do you have a regular primary care provider (e g , primary care physician, family doctor) yes or no',
       "PCP_TYPE":'What type of health care provider is your regular primary care provider ,here the type of the provider is mentioned like family doctor,internist,nurse etc or others ignore the case sensitives in the values',
       "PCP_TYPE_OT":'if health care provider is other ,then who are they mentioned here ignore the case sensitives in the values',
       "PCP_GENDER":'What is the gender identity of your regular primary care provider male or female',
       "PCP_RACE_AI":'race and ethnicity of your regular primary care provider - American Indian or Alaska Native yes or no',
       "PCP_RACE_AS":'race and ethnicity of your regular primary care provider - Asian yes or no',
       "PCP_RACE_BL":'race and ethnicity of your regular primary care provider - Black or African American yes or no',
       "PCP_RACE_HLS":'race and ethnicity of your regular primary care provider - Hispanic, Latino, or Spanish origin yes or no',
       "PCP_RACE_NH":'race and ethnicity of your regular primary care provider - Native Hawaiian or Other Pacific Islander yes or no',
       "PCP_RACE_WH":'race and ethnicity of your regular primary care provider - White yes or no',
       "PCP_RACE_OT":'race and ethnicity of your regular primary care provider if Other yes or no',
       "PCP_RACE_OT_TXT":'race and ethnicity of your regular primary care provider if Other then they are mentioned',
       "PCP_RACE_NS":'Not sure of the race and ethnicity of your regular primary care provider yes or no',
       "CARECOST_POSTPONE":'Postponed seeking medical care due to cost yes or no',
       "CARECOST_WENT_WITHOUT":'Went without needed medical care due to cost yes or no',
       "CARECOST_NO_RX":'Did not take a prescription medication because of drug costs yes or no',
       "CARECOST_NONE":' None of the reasons for the carecost that is didnot postpone seeking medical care due to cost,didnot go without needed medical care due to cost,Did not take a prescription medication because of drug costs',
       "MENO_STATUS":'current menstrual status one of these 1.Peri-menopause / menopause transition (changes in periods, but have not gone 12 months in a row without a period),2.Post-menopause (the years after menopause, more than 12 months in a row without a period),3.Pre-menopause (before menopause having regular periods),4.VeryOften , or left blank',
       "MENO_FOLLOWON":'menopause happened that is post menopause due to 1.chemotherapy or radiation therapy,2.Spontaneous ("natural"),3.Surgical (removal of both ovaries),4.VeryOften, or other reason',
       "MENO_FOLLOWON_TXT":'reason for menopause happened that is post menopause is other  and that reason is specified',
       "HRT":' in the past,or  currently, taking hormone replacement therapy (HRT) options are 1.Yes, I have been on HRT but am not currently,2.Yes, I am currently on HRT,3.No, I do not and have never been on HRT,4.Always',
       "MMG_STATUS":'mamogram status best describes the patient options are 1.I have had a mammogram in the past 12 months,2.I have never had a mammogram,3.I have not had a mammogram in the past 12 months, but I have had a mammogram in the past 24 months,4.I have not had a mammogram in the past 24 months, but I have had a mammogram more than 24 months ago,5.VeryOften',
       "MMG_WHY_GET_TXT":'reasons why patients have mammograms are mentioned',
       "MMG_WHY_NEVER_GET_TXT":'reasons why patients never had mammograms are mentioned',
       "MMG_IMPORTANCE":'How important is having a mammogram to patient- options are on ascale of 1-9,extremely important ,not at all important',
       "MMG_IMPORTANCE_TXT":'Patient explains the importance of mamaogram to them after choosing how important it is to them ',
       "MMG_ADVICE":'What advice about having a mammogram would patient give to other women , advices are noted',
       "MMG_EASIER":'What are one or two things that would make it easier for the patient to have a mammogram every 12 months',
       "BARRIER_NOTKNOW":'Not knowing what is involved with getting a mammogram,how often each of the following issues ever prevented,delayed,or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often',
       "BARRIER_UNSUREBENEFITS":'Unsure about the benefits of getting a mammogram,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often',
       "BARRIER_MISSCANCER":'I heard mammograms miss a lot of cancers,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often',
       "BARRIER_NOHISTORY":'Unnecessary to get a mammogram since breast cancer does not run in my family,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often',
       "BARRIER_NORISK":'Do not have risk factors of breast cancer,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed  options are always,never,rarely,sometimes,very often',
       "BARRIER_TOOYOUNG":'I think I am too young to have a mammogram,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often',
       "BARRIER_TOOHEALTHY":'I think I am too healthy to have breast cancer,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often,no',
       "BARRIER_NOSYMPTOMS":'Do not have any symptoms in my breasts,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often',
       "BARRIER_UNAWAREHOW":'Unaware of how often to get a mammogram,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often,do not remember',
       "BARRIER_INSECURITY":'Insecurity about getting a mammogram,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often,Digital mammography in 3D (digital breast tomosynthesis)',
       "BARRIER_LANGUAGE":'Language barriers since English is not my first/primary language,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed,options are always,never,rarely,sometimes,very often,I am likely to have a mammogram in the next 6 months',
       "BARRIER_PRIVACY":'Concern with privacy issues such as exposure and touching of breasts by a mammogram technician, how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often',
       "BARRIER_PAIN":'Concerns about discomfort or pain with getting a mammogram,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often,50',
       "BARRIER_PREVIOUSNEGATIVE":'Previous negative experience getting a mammogram,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often',
       "BARRIER_FEAREXPERIENCE":'Fears about the mammogram experience,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often',
       "BARRIER_FEARRESULTS":'Fear of the mammogram results,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often',
       "BARRIER_RADIATION":'Concerns about radiation,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often',
       "BARRIER_LACKTRUST":'Lack of trust in the health care system, how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often,Personal vehicle (car or truck)',
       "BARRIER_ANNUAL":'Not getting annual health checkups,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often',
       "BARRIER_NODR":'Not having a doctor that I see on a regular basis,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often,Less than 15 minutes',
       "BARRIER_NOREFERRAL":'Not receiving a referral or recommendation for a mammogram from a doctor or other health care provider,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often',
       "BARRIER_NOINSURANCE":'Not having health insurance coverage for mammograms,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often',
       "BARRIER_NOAFFORD":'Not being able to afford a mammogram,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often,no',
       "BARRIER_TRANSPORTATION":'Problems with transportation,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed  options are always,never,rarely,sometimes,very often ',
       "BARRIER_NOACCESS":'Limited or no access to a mammogram facility nearby,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often,3 hours ',
       "BARRIER_WORK":'Time away from work,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often,1.2',
       "BARRIER_SOCIALSUPPORT":'Little or no social support from family and friends,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often, No Comment',
       "BARRIER_PRIORITIES":'Have competing priorities that are more important than screening,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often,,College graduate (e g , BA, AB, BS, etc ) ',
       "BARRIER_CLINICHRS":'Inconvenient clinic hours,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often,Urban (city) ',
       "BARRIER_SCHEDULING":'Difficulty scheduling an appointment (clinic availability),how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often,Divorced or separated ',
       "BARRIER_GOINGTOAPPT":'Difficulty going to the appointment (child or elder care, unable to leave work),how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often,no',
       "BARRIER_FORGOT":'Forgot or overlooked a scheduled appointment,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often,no',
       "BARRIER_NOTIME":'I dont have time,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often,no',
        "BARRIER_PROCRASTINATE":'Procrastination,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often,no ',
        "BARRIER_DISABILITY":'Knowing that the facilities are not disability-friendly (e g , the physical design/layout of medical rooms and equipment) ,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often,no',
        "BARRIER_TOOSMALL":'I am too small to have cancer, I have small breasts,how often each of the following issues ever prevented, delayed, or interfered with your getting a mammogram when needed options are always,never,rarely,sometimes,very often,no ',
        "BARRIER_OT":' Are there any  other issues that have ever prevented, delayed, or interfered with your getting a mammogram when needed  yes or no',
        "BARRIER_OT_TXT":'if there are other issues that have ever prevented, delayed, or interfered with your getting a mammogram when needed what are they are mentioned',
        "MMG_RESULTS":'results of patient(s) most recent mammogram like normal abnormal,do no remember,do not know,no etc are mentioned',
        "MMG_TYPE":' type of mammogram was patient(s) most recent mammogram like Digital mammography in 2D,Digital mammography in 3D (digital breast tomosynthesis),no,not sure',
        "MMG_FREQ":'How likely is the patient to have a mammogram options are likely in next 3 months,6 months,9 months,2 months,24 months,not likely in the next 24 months,likely to never have,no',
        "MMG_FREQ_3MO":'How likely are you to have a mammogram in the next 3 months on a scale of 1-100',
        "MMG_FREQ_6MO":'How likely are you to have a mammogram in the next 6 months on  ascale of 1-100 ,another answer can be - yes',
        "MMG_FREQ_9MO":'How likely are you to have a mammogram in the next 9 months on a scale of 1-100 , another answer can be - Not employed, looking for work',
        "MMG_FREQ_12MO":'How likely are you to have a mammogram in the next 12 months on a scale of 1-100 ',
        "MMG_FREQ_24MO":'How likely are you to have a mammogram in the next 24 months on a scale of 1-100 , another answer can be - $50,000 to $74,000',
        "MMG_FREQ_BEYOND24MO":'How likely are you to have a mammogram in but not in the next 24 months on a scale of 1-100',
        "MMG_TRANSPORT_TYPE":'How did patient travel to  most recent mammogram screening appointment vehincle types are mentioned here',
        "MMG_TRANSPORT_TYPE_TXT":' if Other (please specify) is given for How did patient travel to  most recent mammogram screening appointment that vehicle or transportation mode is mentioned',
        "MMG_TRANSPORT_TIME":'How much time/long did you travel to receive your most recent mammogram - the time or duration is mentioned',
        "MMG_TRANSPORT_TIME_TXT":'If Other (please specify) is given,How much time/long did you travel to receive your most recent mammogram -that duration or time or other time is mentioned',
        "MMG_REASONABLE_TIME_CLASS_TXT":' if Other (please specify) is given for a reasonable time to travel to receive  next mammogram then the other reason or time/distance is mentioned',
        "MMG_TIMEOFF_WK_YN":'Did patient have to take time off work to receive your most recent mammogram yes or no',
        "MMG_TIMEOFF_WK_PAID":'Was the time taken off work for your most recent mammogram paid or not options are Not paid time off,Paid time off',
        "MMG_TIMEOFF_NEEDED":'How much time did patient or would patient need to take off work to receive a mammogram on a scale of 0-7 hours or an entire day',
        "MMG_REASONABLE_TIME":'What would be a reasonable time to travel to receive your next mammogram on a scale of 0-2400',
        "MMG_ANYTHINGELSE":'Is there anything patient would like to tell  about his/her use of health care services in relation to mammograms ,here patients will express their opinions',
        "EDUCATION":'What is the highest level of education completed',
        "COMMUNITY_TYPE":'How would you describe the community where you currently live options are rural(country),suburban(suburbs),urban(city)',
        "MARITAL_STATUS":'marital status of the patient is mentioned like married,not married,livig with partner,single,divorced,widowed',
        "LIS_SSI":'Supplemental Security Income (SSI)-Did patient receive any in the past year yes or no',
        "LIS_EITC":'The Earned Income Tax Credit (EITC)-Did patient receive any  in the past year yes or no',
        "LIS_DISABILITY":'Disability income-Did patient receive any in the past year yes or no',
        "LIS_WIC":'Food assistancelike  WIC or Supplemental Nutrition Program for Women, Infants, and Children-Did patient receive any  in the past year yes or no',
        "LIS_HOUSING":'Housing help-Did patientreceive any  in the past year yes or no',
        "LIS_UTILITY":'Help with utility bills-Did patient receive any in the past year yes or no',
        "LIS_WELFARE":'Welfare -TANF, or Temporary Assistance for Needy Families-Did patient receive any in the past year yes or no',
        "LIS_BENEFITFINDER":'Benefit finder-Did patient receive any  in the past year yes or no',
        "LIS_MEDICAID":'Medicaid, or the Children Health Insurance Program (CHIP)-Did patient receive any  in the past year yes or no',
        "LIS_SOCIALSERVICES":'Assistance from state social service agencies-Did patient receive any  in the past year yes or no',
        "LIS_OT":'Other type of assistance (please specify)-Did patient receive any other assistance in the past year yes or no',
        "LIS_OT_TXT":'Other type of assistance (please specify)- is recieved by patient in the past year then that assistance is mentioned here',
        "LIS_NONE":'None of these-if patient has not received any assistance beneifts etc in the past year yes or no',
        "EMPLOYMENT":'current employment situation of the patient employed or not- options are employed full time,employed part time,self-employed full time,self-employed part time,not employed looking for work,not employed not looking for work',
        "EMPLOYMENT_OT_TXT":' if Other (please specify) is given by the patient under employment ,then that is mentioned here',
        "INCOME":'household income before taxes -ranges are mentioned here',
        "AHRI_AGE_CAT":'AHRI calculated age categories for comparison to US Census data - here the age ranges are given',
        "AHRI_RACE_CAT":'AHRI calculated race categories- Black alone, White alone and Other are the options',
        "AHRI_CCI_SCORE":'AHRI calculated Charlson Comorbidity Index score- range is from 0 to 10',
        "AHRI_REGION":'AHRI region provided with participant ID - here the regions are south,west,northeast,midwest',
        "AHRI_ED_HS":'AHRI calculated education categories- HS or less , more than HS are the options here HS means High school'
    }


# Construct a description string to include in the prompt
    columns_desc = ", ".join([f"{col}: {desc}" for col, desc in column_descriptions.items()])


    # prompt = f"Convert the following question to an SQLite query using the table '{table_name}': '{question}' Just give the query thats all."
    prompt=f"Convert the following question to an SQLite query using the table '{table_name}' "f"with columns ({columns_desc}): '{question}'. Just give the query, that's all."
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    payload = {
        "model": "gpt-4o",
        "messages": [
        {"role": "system", "content": "You are a sql agent,so treat a Yes as a positive value ,and a No as a negative value.Convert all values to lowercase both the prompt and the values of table and then query the table."},
        {"role": "user", "content": prompt}
    ],
        "max_tokens": 1000
    }

    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        sql_query = response.json()["choices"][0]["message"]["content"].strip()

        # Clean the query if needed
        if sql_query.startswith("```"):
            sql_query = sql_query.split("\n", 1)[1]
            sql_query = sql_query.rsplit("```", 1)[0]
        
        sql_query = sql_query.replace('Sure,', '').strip()
        return sql_query
    
    except requests.exceptions.HTTPError as http_err:
        return {"error": f"HTTP error occurred: {http_err}"}
    except requests.exceptions.RequestException as req_err:
        return {"error": f"Request error occurred: {req_err}"}
    except Exception as err:
        return {"error": f"An error occurred: {err}"}


# Function to handle graphical queries (e.g., plotting data)


# Function to handle graphical queries (e.g., plotting data)
def process_graphical_query(question):
    # Simulated graphical processing logic
    file = client.files.create(
        file=open("data/BrCA Dataset_N5030_lab.csv", "rb"),
        purpose='assistants'
    )

    assistant = client.beta.assistants.create(
        instructions="You are a personal data analyst. Generate a chart for the requested data.",
        name="Chart Maker",
        model="gpt-4o",
        tools=[{"type": "code_interpreter"}],
        tool_resources={"code_interpreter": {"file_ids": [file.id]}}
    )

    thread = client.beta.threads.create()
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role='user',
        content=question
    )

    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)

    while run.status not in ["completed", "failed"]:
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        time.sleep(10)

    messages = client.beta.threads.messages.list(thread_id=thread.id)

    for message in messages:
        for content in message.content:
            if content.type == 'image_file':
                image_data = client.files.content(content.image_file.file_id)
                image_data_bytes = image_data.read()

                # Ensure the directory exists
                image_dir = "static/images"
                os.makedirs(image_dir, exist_ok=True)

                image_filename = f"{image_dir}/{content.image_file.file_id}.png"
                with open(image_filename, "wb") as file:
                    file.write(image_data_bytes)
                return image_filename

    return {"error": "No image generated"}


# Flask route to handle both textual and graphical queries
@app.route('/usa-health', methods=['POST'])
def ask():
    data = request.get_json()
    question = data.get('query')
    if not question:
        return jsonify({"error": "No question provided"}), 400

    # Determine whether to process as text or graphical
    if "plot" in question.lower() or "visual" in question.lower() or "graph" in question.lower() or "draw" in question.lower() or "chart" in question.lower():
        # result = process_graphical_query(question)

        image_filename = process_graphical_query(question)
        if isinstance(image_filename, dict) and "error" in image_filename:
            return jsonify({"error": image_filename["error"]}), 400

        # Return the image file directly
        return send_file(image_filename, mimetype='image/png')

    else:
        sql_query = question_to_sql(question)
        if isinstance(sql_query, dict) and "error" in sql_query:
            return jsonify({"error": sql_query["error"]}), 400

        execution_result = execute_query_with_steps(sql_query)
        if "error" in execution_result:
            return jsonify({"error": execution_result["error"], "steps": execution_result["steps"]}), 400

        return jsonify({"query": sql_query, "data": execution_result["result"], "steps": execution_result["steps"]})

if __name__ == '__main__':
    app.run(debug=True)
