"""
Faktura AI API routes (Invoice Import).

All endpoints require X-API-Key header for authentication.
"""
from flask import Blueprint, request
from app.middleware.auth import require_api_key
from app.utils.response import success_response, error_response
from app.services.faktura_service import FakturaService
import logging

logger = logging.getLogger(__name__)

# Create blueprint with /faktura-ai prefix
faktura_bp = Blueprint('faktura_api', __name__, url_prefix='/faktura-ai')

# Initialize service
faktura_service = FakturaService()


@faktura_bp.route('/import-csv', methods=['POST'])
@require_api_key
def import_csv():
    """
    Import invoices from CSV file.
    
    Form data:
        - file: CSV file (required)
        - mode: 'dry_run' or 'commit' (default: 'dry_run')
    
    Returns:
        JSON with import results
    """
    try:
        # Check if file is present
        if 'file' not in request.files:
            return error_response(
                message="Missing required file",
                code="MISSING_FILE",
                status_code=400
            )
        
        file = request.files['file']
        
        if file.filename == '':
            return error_response(
                message="No file selected",
                code="NO_FILE_SELECTED",
                status_code=400
            )
        
        if not file.filename.lower().endswith('.csv'):
            return error_response(
                message="Invalid file format. Only CSV files are supported.",
                code="INVALID_FILE_FORMAT",
                status_code=400
            )
        
        # Get mode from form data
        mode = request.form.get('mode', 'dry_run')
        
        if mode not in ['dry_run', 'commit']:
            return error_response(
                message="Invalid mode. Supported modes: dry_run, commit",
                code="INVALID_MODE",
                status_code=400
            )
        
        # Read file content
        file_content = file.read().decode('utf-8')
        
        # Import CSV
        result = faktura_service.import_csv(file_content, mode)
        
        if result['status'] == 'error':
            return error_response(
                message=result['message'],
                code=result.get('code', 'CSV_IMPORT_ERROR'),
                status_code=400
            )
        
        logger.info(f"POST /faktura-ai/import-csv: mode={mode}, items={result['totals']['processed']}")
        return success_response(data=result, message=result['message'])
        
    except Exception as e:
        logger.error(f"Error importing CSV: {str(e)}")
        return error_response(
            message=f"Failed to import CSV: {str(e)}",
            code="CSV_IMPORT_ERROR",
            status_code=500
        )


@faktura_bp.route('/import-xml/parse', methods=['POST'])
@require_api_key
def parse_xml():
    """
    Parse XML invoice without committing to database.
    
    Form data:
        - file: XML file (required)
    
    Returns:
        JSON with parsed invoice data
    """
    try:
        # Check if file is present
        if 'file' not in request.files:
            return error_response(
                message="Missing required file",
                code="MISSING_FILE",
                status_code=400
            )
        
        file = request.files['file']
        
        if file.filename == '':
            return error_response(
                message="No file selected",
                code="NO_FILE_SELECTED",
                status_code=400
            )
        
        if not file.filename.lower().endswith('.xml'):
            return error_response(
                message="Invalid file format. Only XML files are supported.",
                code="INVALID_FILE_FORMAT",
                status_code=400
            )
        
        # Read file content
        file_content = file.read().decode('utf-8')
        
        # Parse XML
        result = faktura_service.parse_xml(file_content)
        
        if result['status'] == 'error':
            return error_response(
                message=result['message'],
                code=result.get('code', 'XML_PARSE_ERROR'),
                status_code=400
            )
        
        logger.info(f"POST /faktura-ai/import-xml/parse: items={result['totals']['items_count']}")
        return success_response(data=result, message=result['message'])
        
    except Exception as e:
        logger.error(f"Error parsing XML: {str(e)}")
        return error_response(
            message=f"Failed to parse XML: {str(e)}",
            code="XML_PARSE_ERROR",
            status_code=500
        )


@faktura_bp.route('/import-xml/commit', methods=['POST'])
@require_api_key
def commit_xml():
    """
    Parse and commit XML invoice to database.
    
    Form data:
        - file: XML file (required)
    
    Returns:
        JSON with commit results
    """
    try:
        # Check if file is present
        if 'file' not in request.files:
            return error_response(
                message="Missing required file",
                code="MISSING_FILE",
                status_code=400
            )
        
        file = request.files['file']
        
        if file.filename == '':
            return error_response(
                message="No file selected",
                code="NO_FILE_SELECTED",
                status_code=400
            )
        
        if not file.filename.lower().endswith('.xml'):
            return error_response(
                message="Invalid file format. Only XML files are supported.",
                code="INVALID_FILE_FORMAT",
                status_code=400
            )
        
        # Read file content
        file_content = file.read().decode('utf-8')
        
        # Commit XML
        result = faktura_service.commit_xml(file_content)
        
        if result['status'] == 'error':
            return error_response(
                message=result['message'],
                code=result.get('code', 'XML_COMMIT_ERROR'),
                status_code=400
            )
        
        logger.info(f"POST /faktura-ai/import-xml/commit: invoice={result['invoice_no']}")
        return success_response(data=result, message=result['message'])
        
    except Exception as e:
        logger.error(f"Error committing XML: {str(e)}")
        return error_response(
            message=f"Failed to commit XML: {str(e)}",
            code="XML_COMMIT_ERROR",
            status_code=500
        )
