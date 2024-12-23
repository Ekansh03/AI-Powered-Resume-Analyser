try:
    # Import necessary modules
    from resume_parser import analyze_resume
    import json

    # Load the skills data
    with open("skills_data.json", "r") as file:
        skills_data = json.load(file)

    # Run the resume analysis
    result = analyze_resume("sample_resumes/EkanshMotiani_resume.pdf", skills_data)

    # Save the result to a JSON file
    with open("result.json", "w") as outfile:
        json.dump(result, outfile, indent=4)

    print("Results saved to result.json")

except FileNotFoundError as e:
    print(f"Error: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
