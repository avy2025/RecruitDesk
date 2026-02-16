
import requests
import time
import os

API_URL = "http://localhost:8000"

def wait_for_server(timeout=60):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{API_URL}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"Server is up: {data}")
                if data.get("model") == "all-mpnet-base-v2" or data.get("model") == "all-MiniLM-L6-v2":
                    return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(2)
        print("Waiting for server...")
    return False

def test_ranking():
    # Create a dummy resume PDF
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Python Developer Resume", ln=1, align="C")
    pdf.cell(200, 10, txt="Skills: Python, FastAPI, Docker, Kubernetes, AWS", ln=1)
    pdf.cell(200, 10, txt="Experience: worked 5 years as backend developer using Django and Flask.", ln=1)
    pdf.output("dummy_resume.pdf")

    # Define job description
    job_description = "We are looking for a Python Developer with experience in FastAPI, Docker, and AWS."

    # Send request
    files = {'resumes': open('dummy_resume.pdf', 'rb')}
    data = {'job_description': job_description}
    
    print("\nTesting ranking endpoint...")
    response = requests.post(f"{API_URL}/rank-resumes", files=files, data=data)
    
    if response.status_code == 200:
        result = response.json()
        print("Success!")
        print(f"Total Resumes: {result['total_resumes']}")
        if result['ranked_resumes']:
            top_result = result['ranked_resumes'][0]
            print(f"Top Match: {top_result['filename']} - {top_result['match_percentage']}%")
            print("Match Details:")
            details = top_result.get('match_details', {})
            print(f"- Semantic Score: {details.get('semantic_score')}")
            print(f"- Keyword Score: {details.get('keyword_score')}")
            print(f"- Matched Skills: {details.get('matched_skills')}")
            print(f"- Reasons: {details.get('match_reasons')}")
            
            # assertions
            if 'semantic_score' in details and 'matched_skills' in details:
                print("\nVerification PASSED: Match details present.")
            else:
                print("\nVerification FAILED: Missing match details.")
        else:
            print("\nVerification FAILED: No results returned.")
    else:
        print(f"\nVerification FAILED: API Error {response.status_code} - {response.text}")

    # Cleanup
    files['resumes'].close()
    if os.path.exists("dummy_resume.pdf"):
        os.remove("dummy_resume.pdf")

if __name__ == "__main__":
    if wait_for_server():
        test_ranking()
    else:
        print("Server failed to start or is not reachable.")
