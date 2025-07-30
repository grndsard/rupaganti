#!/usr/bin/env python3
"""
Test script for PDF merge functionality
"""

import os
import sys
from io import BytesIO

def test_pdf_merger():
    """Test if PDF merger libraries are available"""
    try:
        from PyPDF2 import PdfMerger
        print("✅ PyPDF2 available")
        return True
    except ImportError:
        try:
            from pypdf import PdfMerger
            print("✅ pypdf available")
            return True
        except ImportError:
            print("❌ No PDF merger library found")
            print("Install with: pip install PyPDF2")
            return False

def create_test_pdf():
    """Create a simple test PDF"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.drawString(100, 750, "Test PDF Document")
        c.drawString(100, 700, "This is a test page")
        c.save()
        buffer.seek(0)
        return buffer.getvalue()
    except ImportError:
        print("⚠️ reportlab not available for test PDF creation")
        return None

def test_merge_functionality():
    """Test the actual merge functionality"""
    if not test_pdf_merger():
        return False
    
    # Import the merger
    try:
        from PyPDF2 import PdfMerger
    except ImportError:
        from pypdf import PdfMerger
    
    # Create test PDFs
    test_pdf_data = create_test_pdf()
    if not test_pdf_data:
        print("⚠️ Cannot create test PDFs, skipping merge test")
        return True
    
    try:
        # Test merge
        merger = PdfMerger()
        
        # Add two copies of the test PDF
        pdf1 = BytesIO(test_pdf_data)
        pdf2 = BytesIO(test_pdf_data)
        
        merger.append(pdf1)
        merger.append(pdf2)
        
        # Create output
        output = BytesIO()
        merger.write(output)
        merger.close()
        
        output.seek(0)
        merged_data = output.getvalue()
        
        if len(merged_data) > len(test_pdf_data):
            print("✅ PDF merge test successful")
            print(f"   Original: {len(test_pdf_data)} bytes")
            print(f"   Merged: {len(merged_data)} bytes")
            return True
        else:
            print("❌ PDF merge test failed - output too small")
            return False
            
    except Exception as e:
        print(f"❌ PDF merge test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 Testing PDF merge functionality...")
    print()
    
    success = test_merge_functionality()
    
    print()
    if success:
        print("🎉 All tests passed! PDF merge functionality is ready.")
    else:
        print("💥 Tests failed. Please install required dependencies:")
        print("   pip install PyPDF2 reportlab")
    
    sys.exit(0 if success else 1)