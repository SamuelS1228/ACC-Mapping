# Cluster Site Mapper

A Streamlit app that lets you upload a site file, map each site, filter by cluster, and assign custom colors by cluster for presentation-ready screenshots.

## Expected input columns
Your upload file should contain these columns:

- Store Number
- City
- State
- lat
- lng
- Cluster

Excel (`.xlsx`, `.xls`) and CSV uploads are supported.

## Features
- Upload an Excel or CSV file
- Plot every site on a light-theme map
- Filter which clusters are shown
- Pick a custom color for each cluster
- Adjust point size and map height
- Export the filtered data

## Local setup
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy with GitHub + Streamlit Community Cloud
1. Create a new GitHub repo.
2. Upload the contents of this folder.
3. In Streamlit Community Cloud, create a new app and point it to `app.py`.
4. Deploy.

## Notes
- The map uses the `carto-positron` basemap for a clean, light presentation style.
- The app standardizes minor column naming differences, but the six required fields must be present.
