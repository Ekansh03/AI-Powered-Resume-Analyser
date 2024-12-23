# resume_parser.py

import json

def analyze_resume(file_path, skills_data):
    try:
        # Read the resume (for now, we will assume it's a text file, adjust accordingly for PDFs)
        with open(file_path, 'r') as file:
            resume_text = file.read()

        # Initialize result
        result = {"skills": []}

        # Check for skills in the resume
        for skill in skills_data.get("skills", []):
            if skill.lower() in resume_text.lower():
                result["skills"].append(skill)

        return result
    except Exception as e:
        return {"error": str(e)}
