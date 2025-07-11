FileFusion


docker run -p 65432:65432 -v "${PWD}\uploads:/app/uploads" -v "${PWD}\converted:/app/converted" filefusion-backend


cd backend
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On Linux/Mac

venv\Scripts\activate
python server.py



cd frontend
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On Linux/Mac

pip install -r requirements.txt
streamlit run client.py


docker build -t filefusion-backend .