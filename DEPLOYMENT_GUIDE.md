# MedSafe – AI Medication Safety Chatbot
## Complete Deployment Guide (Zero Coding Knowledge Required)
### MIS685 Project – Maitri Jagdishbhai Dabhiya & Heli Dipakkumar Patel

---

> **What you will build:** A public website where users type their medications and foods, and an AI chatbot powered by Amazon Bedrock (Claude) checks a drug interaction graph database (Amazon Neptune) and replies with safety information.

---

## Table of Contents
1. Prerequisites & Account Setup
2. Install Required Tools on Your Computer
3. Download and Understand the Project Files
4. Generate the Drug Interaction Dataset
5. Deploy Everything to AWS (CDK)
6. Load the Drug Interaction Data into Neptune
7. Enable Amazon Bedrock Claude Model Access
8. Connect the Website to Your API
9. Test Your Chatbot
10. Expected Outputs at Each Step
11. Troubleshooting Guide

---

## STEP 1 — Create an AWS Account (Skip if you have one)

### 1a. Sign Up
1. Go to **https://aws.amazon.com** and click **"Create an AWS Account"**
2. Enter your email address and choose an account name (e.g., `MIS685-Project`)
3. Choose **"Personal"** account type
4. Enter payment information (a credit card is required but you will stay within free tier for most services)
5. Verify your phone number
6. Choose **"Basic Support – Free"**
7. Sign in to the **AWS Console** at **https://console.aws.amazon.com**

**Expected Output ✅:** You can see the AWS Management Console dashboard.

---

### 1b. Create an IAM User (Recommended – Don't use root)
1. In the AWS Console search bar, type **IAM** and click it
2. Click **"Users"** → **"Create user"**
3. Username: `medsafe-admin`
4. Check **"Provide user access to the AWS Management Console"**
5. Select **"I want to create an IAM user"**
6. Set a password
7. Click **"Next"** → **"Attach policies directly"**
8. Search for and check: **AdministratorAccess**
9. Click **"Create user"**
10. **Download the CSV file** with your Access Key ID and Secret Access Key — save it safely!

**Expected Output ✅:** A new IAM user exists. You have a CSV with Access Key ID and Secret Access Key.

---

## STEP 2 — Install Required Tools on Your Computer

You need to install three tools. Follow the instructions for your operating system.

### 2a. Install Python 3.11+
- **Windows:** Download from https://python.org/downloads — check "Add Python to PATH" during install
- **Mac:** Open Terminal and run: `brew install python` (install Homebrew first from https://brew.sh if needed)
- **Verify:** Open a terminal/command prompt and run: `python --version`
- **Expected Output ✅:** Shows `Python 3.11.x` or higher

### 2b. Install Node.js (Required for CDK)
- Download from **https://nodejs.org** — choose the **LTS version**
- Install it (click Next through all steps)
- **Verify:** Run `node --version` in terminal
- **Expected Output ✅:** Shows `v18.x.x` or higher

### 2c. Install AWS CLI
- **Windows:** Download from https://aws.amazon.com/cli/ → Windows installer (.msi)
- **Mac:** Run `brew install awscli` in Terminal
- **Verify:** Run `aws --version`
- **Expected Output ✅:** Shows `aws-cli/2.x.x`

### 2d. Configure AWS CLI with Your Credentials
Run in your terminal:
```
aws configure
```
It will ask four questions:
```
AWS Access Key ID [None]: PASTE_YOUR_ACCESS_KEY_HERE
AWS Secret Access Key [None]: PASTE_YOUR_SECRET_KEY_HERE
Default region name [None]: us-east-1
Default output format [None]: json
```
**Expected Output ✅:** No errors. Run `aws sts get-caller-identity` and it shows your account number.

### 2e. Install AWS CDK
```
npm install -g aws-cdk
```
**Verify:** Run `cdk --version`
**Expected Output ✅:** Shows `2.x.x`

---

## STEP 3 — Set Up the Project Files

### 3a. Download the Project
All project files are provided to you. Create a folder on your computer:
```
mkdir medsafe-project
cd medsafe-project
```

Place all provided files into this folder. The structure should look like:
```
medsafe-project/
├── data/
│   ├── drug_interactions.csv         ← Your drug interaction dataset
│   ├── generate_neptune_data.py      ← Script to convert dataset for Neptune
├── cdk/
│   ├── app.py                        ← CDK entry point
│   ├── med_safety_stack.py           ← All AWS infrastructure defined here
│   ├── cdk.json                      ← CDK configuration
│   ├── requirements.txt              ← Python packages for CDK
├── lambda/
│   ├── handler.py                    ← Lambda function code
│   ├── requirements.txt              ← Lambda Python packages
├── frontend/
│   └── index.html                    ← Your chatbot website
```

---

## STEP 4 — Generate the Neptune Dataset

### 4a. Run the Dataset Generator
Open your terminal, navigate to the `data/` folder, and run:
```
cd medsafe-project/data
python generate_neptune_data.py
```

**Expected Output ✅:**
```
✅ Created neptune_vertices.csv with 45 nodes
✅ Created neptune_edges.csv with 65 edges
Next: Upload both files to your S3 bucket under the path: neptune-data/
```

You will now have two new files:
- `neptune_vertices.csv` — All drugs, foods, and substances as nodes
- `neptune_edges.csv` — All interactions as relationships

---

## STEP 5 — Package the Lambda Layer (gremlinpython)

The Lambda function needs the `gremlinpython` library to talk to Neptune. We package it as a Layer.

Run these commands in your terminal:
```
cd medsafe-project/lambda
pip install gremlinpython -t layer/python/
```

**Expected Output ✅:** A new folder `lambda/layer/python/` containing gremlinpython files appears.

---

## STEP 6 — Bootstrap and Deploy with CDK

### 6a. Install CDK Python dependencies
```
cd medsafe-project/cdk
python -m venv .venv
```

**On Windows:**
```
.venv\Scripts\activate
```
**On Mac/Linux:**
```
source .venv/bin/activate
```

Then:
```
pip install -r requirements.txt
```
**Expected Output ✅:** Packages install without errors.

### 6b. Bootstrap CDK (One-time setup per account/region)
```
cdk bootstrap aws://YOUR_ACCOUNT_ID/us-east-1
```
Replace `YOUR_ACCOUNT_ID` with your 12-digit AWS account number (find it in the top right of the AWS Console).

**Expected Output ✅:**
```
✅  Environment aws://123456789012/us-east-1 bootstrapped.
```

### 6c. Deploy the Stack
```
cdk deploy
```
When asked "Do you wish to deploy these changes (y/n)?" — type **y** and press Enter.

This will take **10–15 minutes** to create all resources.

**Expected Output ✅:**
```
✅  MedSafetyStack

Outputs:
MedSafetyStack.WebsiteURL = https://abc123xyz.cloudfront.net
MedSafetyStack.ApiEndpoint = https://xyz.execute-api.us-east-1.amazonaws.com/prod/
MedSafetyStack.NeptuneEndpoint = your-cluster.xxxx.us-east-1.neptune.amazonaws.com
MedSafetyStack.DataBucketName = medsafetystack-medsafetydatabucket-xxxxx
MedSafetyStack.NeptuneS3RoleArn = arn:aws:iam::123456789012:role/MedSafetyStack-NeptuneS3Role-xxxx

Stack ARN: arn:aws:cloudformation:us-east-1:...
```
**📌 SAVE ALL THESE OUTPUT VALUES — you will need them in the next steps.**

---

## STEP 7 — Upload Neptune Data to S3

### 7a. Upload the CSV files
Use the `DataBucketName` from Step 6 output:
```
aws s3 cp data/neptune_vertices.csv s3://YOUR_DATA_BUCKET_NAME/neptune-data/neptune_vertices.csv
aws s3 cp data/neptune_edges.csv s3://YOUR_DATA_BUCKET_NAME/neptune-data/neptune_edges.csv
```

**Expected Output ✅:**
```
upload: data/neptune_vertices.csv to s3://medsafetystack-xxx/neptune-data/neptune_vertices.csv
upload: data/neptune_edges.csv to s3://medsafetystack-xxx/neptune-data/neptune_edges.csv
```

---

## STEP 8 — Load Data into Neptune

Neptune has a built-in bulk loader. You'll trigger it via the AWS CLI.

### 8a. Find your Neptune cluster endpoint
Use the `NeptuneEndpoint` from Step 6 output.

### 8b. Load vertices (nodes)
```
aws neptune-graph start-import-task \
  --graph-identifier your-cluster-xxxx \
  --source s3://YOUR_DATA_BUCKET_NAME/neptune-data/neptune_vertices.csv \
  --format CSV \
  --role-arn YOUR_NEPTUNE_S3_ROLE_ARN \
  --region us-east-1
```

**Note:** Neptune bulk load requires a slightly different approach through the Neptune console. Here is the alternative method:

1. Go to **AWS Console → Neptune → Databases**
2. Click on your cluster name
3. Select **"Load data"** tab
4. Fill in:
   - **S3 URI:** `s3://YOUR_DATA_BUCKET_NAME/neptune-data/`
   - **IAM role:** Select the `NeptuneS3Role` created by CDK
   - **Format:** CSV
   - **Region:** us-east-1
5. Click **"Load"**

**Expected Output ✅:** Status shows **"LOAD_COMPLETED"** (takes 1–2 minutes).

---

## STEP 9 — Enable Bedrock Claude Model Access

By default, Bedrock models are not enabled. You must request access:

1. Go to **AWS Console → Amazon Bedrock**
2. In the left sidebar click **"Model access"**
3. Click **"Manage model access"**
4. Find **"Anthropic"** section — check the box for:
   - ✅ **Claude 3 Sonnet**
5. Click **"Request model access"**
6. Wait 1–5 minutes for approval (usually instant for Claude 3 Sonnet)

**Expected Output ✅:** Status shows **"Access granted"** (green checkmark) next to Claude 3 Sonnet.

---

## STEP 10 — Connect the Website to Your API

### 10a. Edit index.html
Open `frontend/index.html` in any text editor (Notepad, TextEdit, VS Code).

Find this line (around line 200):
```javascript
const API_ENDPOINT = "YOUR_API_GATEWAY_URL_HERE/chat";
```

Replace `YOUR_API_GATEWAY_URL_HERE` with the `ApiEndpoint` value from Step 6 output.

Example:
```javascript
const API_ENDPOINT = "https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod/chat";
```

Save the file.

### 10b. Re-upload the website
```
aws s3 sync frontend/ s3://YOUR_WEBSITE_BUCKET_NAME/ --delete
```

Find your website bucket name in the AWS Console → S3, it will be named something like `medsafetystack-websitebucket-xxxx`.

### 10c. Invalidate CloudFront cache
```
aws cloudfront create-invalidation \
  --distribution-id YOUR_CLOUDFRONT_DISTRIBUTION_ID \
  --paths "/*"
```
Find your distribution ID in AWS Console → CloudFront.

**Expected Output ✅:** Files sync without error. Cache invalidation shows status `InProgress` then `Completed`.

---

## STEP 11 — Test Your Chatbot

1. Open the `WebsiteURL` from Step 6 in your browser (e.g., `https://abc123xyz.cloudfront.net`)
2. You should see the MedSafe chatbot interface
3. Click one of the example prompts, or type:
   > *"I'm taking Warfarin and I want to take Aspirin for my headache. Is that safe?"*
4. Press Enter or click the Send button

**Expected Output ✅:**
- The bot shows three animated dots while thinking (1–3 seconds)
- A response appears like:
  > "⚠️ **Important warning about Warfarin + Aspirin:**
  > Combining these two medications significantly increases your risk of bleeding. This is considered a **HIGH** severity interaction..."

5. Try another example:
   > *"I take Simvastatin every evening. Can I have a glass of grapefruit juice with my breakfast?"*

**Expected Output ✅:**
- The bot explains that grapefruit juice contains compounds (furanocoumarins) that block the enzyme that breaks down Simvastatin, leading to toxic buildup in the blood.

---

## Summary of All AWS Resources Created

| Resource | Purpose | Cost Estimate |
|---|---|---|
| Amazon Neptune (t3.medium) | Graph database storing drug interactions | ~$0.10/hr ≈ $72/mo |
| AWS Lambda | Runs the chatbot logic | Free tier (1M requests/mo) |
| Amazon API Gateway | Exposes REST endpoint to website | Free tier (1M calls/mo) |
| Amazon S3 (2 buckets) | Stores website files + Neptune data | < $1/mo |
| Amazon CloudFront | Serves website globally via CDN | Free tier (1TB/mo) |
| Amazon Bedrock (Claude 3 Sonnet) | AI model for responses | Pay per use (~$0.003 per chat) |
| VPC + NAT Gateway | Networking for Neptune | ~$0.045/hr ≈ $32/mo |

**Total estimated cost for a class project: ~$4–6/day while running.**
**To save money: run `cdk destroy` when not using it.**

---

## Troubleshooting

**"Neptune connection timeout"**
→ Check that your Lambda security group allows outbound port 8182 to the Neptune security group. Verify both Lambda and Neptune are in the same VPC.

**"Bedrock AccessDeniedException"**
→ You haven't enabled model access yet (Step 9). Also verify the Lambda IAM role has `bedrock:InvokeModel` permission (it should — CDK adds it).

**"The API endpoint hasn't been configured yet"**
→ You haven't updated index.html with the real API Gateway URL (Step 10a).

**"No interactions found" but you expect some**
→ The Neptune load may not have completed. Check the load status in the Neptune console. Also ensure the drug names in your question match the dataset (e.g., "Warfarin" not "warfin").

**CDK deploy fails with "bootstrap" error**
→ Run `cdk bootstrap aws://YOUR_ACCOUNT_ID/us-east-1` first (Step 6b).

**CDK deploy fails with credentials error**
→ Re-run `aws configure` and make sure your Access Key and Secret Key are correct.

---

## Deleting Everything (To Avoid Charges)

When your project is done:
```
cd medsafe-project/cdk
cdk destroy
```
Type **y** when prompted. This deletes all created resources.

**Expected Output ✅:**
```
✅  MedSafetyStack: destroyed
```
