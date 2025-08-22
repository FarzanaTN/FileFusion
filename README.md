# FileFusion

FileFusion is a computer networking project that provides file conversion capabilities through a client-server architecture. The application consists of a Python backend server and a Streamlit frontend client for seamless file processing. It is our Computer Networking course (CSE-3111) project.

## Features

- File conversion functionality
- Client-server architecture
- ACK based transmission
- Selective Repeat 
- Python-based backend server
- Streamlit web interface
- Real-time file processing

## Prerequisites

Before running FileFusion, ensure you have the following installed:

- Python 3.7 or higher
- pip (Python package installer)
- Git

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/FarzanaTN/FileFusion.git
   cd FileFusion
   ```

2. **Install required dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
   ```bash
   cd frontend
   pip install -r requirements.txt
   ```

   

## Project Structure

```
FileFusion/
├── backend/
│    ├── server.py
|    ├── converter.py
|    └── requirements.txt
├── frontend/
│   ├── client.py
│   └── requirements.txt
├── README.md
└── requirements.txt
```

## How to Run

FileFusion requires two terminals to run simultaneously - one for the backend server and one for the frontend client.

### Step 1: Start the Backend Server

1. Open your first terminal
2. Navigate to the backend directory:
   ```bash
   cd FileFusion/backend
   ```
3. Run the server:
   ```bash
   python3 server.py
   ```

The server will start and begin listening for client connections.

### Step 2: Start the Frontend Client

1. Open a second terminal
2. Navigate to the frontend directory:
   ```bash
   cd FileFusion/frontend
   ```
3. Run the Streamlit client:
   ```bash
   streamlit run client.py
   ```

The Streamlit application will automatically open in your default web browser, typically at `http://localhost:8501`.

## Usage

1. Ensure both the backend server and frontend client are running
2. Open your web browser and go to the Streamlit interface (usually `http://localhost:8501`)
3. Use the web interface to upload and convert files
4. The frontend will communicate with the backend server to process your files

## Troubleshooting

- **Port conflicts**: If you encounter port conflicts, check that no other applications are using the default ports
- **Connection issues**: Ensure both server and client are running and can communicate with each other
- **Dependencies**: Make sure all required Python packages are installed

## Configuration

You may need to configure:
- Server port and host settings in `backend/server.py`
- Client connection settings in `frontend/client.py`
- File upload/download directories



## Support

If you encounter any issues or have questions, please:
1. Check the troubleshooting section above
2. Review the project documentation
3. Open an issue on the GitHub repository

## Development

For development purposes:
- Backend server code is located in `backend/server.py`
- Frontend client code is located in `frontend/client.py`
- Make sure to test both components after making changes

---

**Note**: Remember to keep both terminals open while using FileFusion, as the application requires both the backend server and frontend client to be running simultaneously.

## 📹 Project Demonstration

Watch our FileFusion demo video:

👉 [Click here to watch the video](https://drive.google.com/file/d/1gffLQrfsgSOxhtXkGQZ61vLsyakRjsf9/view?usp=sharing)
