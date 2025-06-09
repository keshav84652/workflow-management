# CPA Copilot - Tax Professional Assistant

An intelligent web application designed to serve as a copilot for tax professionals, streamlining tax preparation through automated document processing, AI-powered analysis, and intelligent workpaper generation.

## 🚀 Features

### Current MVP Features
1. **Smart Document Upload**
   - Single and batch file uploads
   - Support for PDF, JPG, PNG, TIFF formats
   - Drag-and-drop interface
   - Progress tracking for batch uploads

2. **Azure Document Intelligence Integration**
   - Automated tax document recognition using `prebuilt-tax.us` model
   - Extraction of key fields from W-2s, 1099s, 1040s, and other tax forms
   - High-accuracy data extraction with confidence scores

3. **Gemini AI Document Understanding**
   - Multi-modal document analysis
   - Document categorization and professional summaries
   - Structured data extraction in JSON format
   - Intelligent bookmark structure suggestions for workpaper organization

4. **Comprehensive Data Processing**
   - PII handling with masking/removal options
   - Data validation and error checking
   - Export capabilities (JSON, CSV, processed data)
   - Side-by-side comparison of Azure and Gemini extractions

5. **Intelligent Workpaper Generation**
   - Automated PDF consolidation
   - Hierarchical bookmark structure (3 levels: Category → File Type → Specifics)
   - Professional workpaper formatting
   - Easy navigation and document organization

### Planned Features
- Agentic tax preparer bot for automated form filling
- Tax research assistant with real-time regulation updates
- Multi-year comparison and trend analysis
- Client portal integration
- Advanced compliance checking

## 🏗️ Architecture

```
CPA_copilot/
├── backend/                 # Core business logic (frontend-agnostic)
│   ├── services/           # Service layer
│   │   ├── azure_service.py           # Azure Document Intelligence integration
│   │   ├── gemini_service.py          # Google Gemini AI integration
│   │   ├── document_processor.py      # Main document processing orchestrator
│   │   ├── document_visualizer.py     # Field visualization on documents
│   │   └── workpaper_generator.py     # PDF workpaper generation
│   ├── models/             # Data models (Pydantic V2)
│   │   ├── document.py               # Core document models
│   │   └── tax_forms.py              # Tax form specific models
│   ├── utils/              # Utilities
│   │   ├── config.py                 # Configuration management
│   │   ├── validators.py             # Data validation utilities
│   │   └── file_handlers.py          # File processing utilities
│   └── enhanced_tax_processor.py     # Advanced tax processing library
├── frontend/               # Multiple frontend implementations
│   ├── streamlit/         # Production-ready Streamlit interface
│   │   └── app.py                   # Main Streamlit application
│   └── react/             # Modern React frontend (React + TypeScript + Tailwind)
│       ├── src/
│       │   ├── components/          # Reusable React components
│       │   ├── pages/              # Application pages
│       │   ├── hooks/              # Custom React hooks
│       │   ├── services/           # API integration services
│       │   └── types/              # TypeScript type definitions
│       ├── public/                 # Static assets
│       └── package.json            # Node.js dependencies
├── docs/                   # Documentation
├── temp/                   # Temporary file storage
│   ├── uploads/           # Document uploads
│   └── workpapers/        # Generated workpapers
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── fixtures/          # Test data
└── requirements.txt        # Python dependencies
```

## 🛠️ Technology Stack

### Backend
- **Python 3.9+** - Core application runtime
- **FastAPI** - High-performance web framework (planned)
- **Pydantic V2** - Data validation and serialization
- **AsyncIO** - Asynchronous processing

### AI/ML Services
- **Azure Document Intelligence** - OCR and form recognition
- **Google Gemini AI** - Document understanding and analysis
- **Model**: `gemini-2.5-flash-preview-05-20`

### Frontend Options
- **Streamlit** - Production-ready interface (current)
- **React + TypeScript + Tailwind CSS** - Modern web interface
- **Vite** - Fast build tool for React development

### Document Processing
- **PyPDF2** - PDF manipulation and merging
- **Pillow (PIL)** - Image processing
- **img2pdf** - Image to PDF conversion
- **OpenCV** - Document visualization

### Data & Storage
- **pandas** - Data manipulation and analysis
- **JSON/CSV** - Export formats
- **File system** - Temporary document storage

## 📋 Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/CPA_copilot.git
cd CPA_copilot
```

2. Create a virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On macOS/Linux
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
copy .env.example .env
# Edit .env with your API keys and configuration
```

5. Run the Streamlit app:
```bash
streamlit run frontend/streamlit/app.py
```

## 🔧 Configuration

Create a `.env` file in the root directory with the following:

```env
# Azure Document Intelligence
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://cpa-flow.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your_key_here

# Google Gemini AI
GEMINI_API_KEY=your_gemini_key_here
GEMINI_MODEL=gemini-2.5-flash-preview-05-20

# Application Settings
UPLOAD_FOLDER=temp/uploads
MAX_FILE_SIZE=10485760  # 10MB
ALLOWED_EXTENSIONS=pdf,jpg,jpeg,png,tiff
```

## 🚦 Usage

1. **Upload Documents**: Drag and drop tax documents or use the file browser
2. **Process Documents**: Click "Process Documents" to run Azure and Gemini analysis
3. **Review Results**: View extracted data, summaries, and validation results
4. **Generate Workpaper**: Create a consolidated PDF with intelligent bookmarking
5. **Export Data**: Download raw JSON, processed data, or CSV exports

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test modules
pytest tests/test_azure_service.py
pytest tests/test_gemini_service.py
```

## 📝 Development Guidelines

1. **Separation of Concerns**: Keep business logic in the backend, UI logic in frontend
2. **Error Handling**: Comprehensive try-catch blocks with meaningful error messages
3. **Logging**: Use Python's logging module for debugging and monitoring
4. **Type Hints**: Use type annotations for better code maintainability
5. **Documentation**: Document all functions and classes with docstrings

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is proprietary software. All rights reserved.

## 🙏 Acknowledgments

- Azure Document Intelligence team for the powerful prebuilt tax models
- Google Gemini team for advanced multi-modal AI capabilities
- The open-source community for amazing Python libraries

## 📞 Support

For questions or support, please contact the development team.
