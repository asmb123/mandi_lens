You're setting up Sarvam AI in this project. Get me to one working API call — nothing more.

1. Install the Sarvam SDK — pip install sarvamai
2. Create a .env file with SARVAM_API_KEY=, and add .env to .gitignore. Read the key from the environment; never hardcode or print it.
3. Write one short script that initializes the Sarvam client and makes a chat completion call with the sarvam-105b-conversations model, then prints the reply.
4. Stop here and tell me to paste my key into .env. Don't work around the missing key — no dummy values, no test requests without it.
5. When I confirm the key is in, run the script and show me the output.
6. Then ask me what I want to build with Sarvam, and use https://docs.sarvam.ai/api/getting-started/welcome to find the right API for it.

Create the files in this project's directory. If this doesn't look like a project, ask me where to put them before creating anything.
Keep it minimal — no extra dependencies or scaffolding I didn't ask for.