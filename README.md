# Desh Ke Haath

A demonstration marketplace for Indian handicrafts, artisans, and regional traditions.

## Run locally

Install Python 3.10 or newer, then create and activate a virtual environment and install the dependencies:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5001 in your browser. This is a demo; checkout, artisan profiles, and vendor review are not production services.

Voice search requires a compatible browser and microphone permission. Image and location search have browser and network limitations.

## Image generation

The current web generator requires a configured image provider and may use paid credits. Copy `.env.example` to `.env` and configure the provider locally; never commit keys. A local Mac image generator has not been implemented yet.

## Mac app download

There is no Mac app or installer release yet. When a build has been created and tested, downloads can be published on the [Releases page](https://github.com/dheerajchalla58-commits/deshkahaath-1/releases).
