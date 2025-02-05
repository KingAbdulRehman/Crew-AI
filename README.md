# Crew-AI

# First Project Test Flow with Gemini
## Setup

1. Create a test flow project:
    ```sh
    crewai create flow CrewTestFlow
    ```

2. Navigate to the project directory:
    ```sh
    cd CrewTestFlow
    ```

3. Set up your `.env` file with your API key and model:
    ```env
    GEMINI_API_KEY=YOUR_API_KEY
    MODEL=gemini/gemini-2.0-flash-exp
    ```

    **Note:** Do not push your `.env` file to version control.

4. Run the project:
    ```sh
    uv run kickoff
    ```