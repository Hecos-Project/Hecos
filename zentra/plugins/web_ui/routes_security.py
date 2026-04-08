"""
MODULE: Web UI Security Routes
DESCRIPTION: Exposes endpoints to download the Local Root CA certificate.
"""
import os
from flask import send_file, jsonify, request
from flask_login import login_required

def init_security_routes(app, logger):

    @app.route('/api/security/download-ca', methods=['GET'])
    @login_required # Protected! Only authenticated users can download
    def download_root_ca():
        ca_path = os.path.abspath("certs/ca/rootCA.pem")
        if not os.path.exists(ca_path):
            return jsonify({"error": "Root CA not found. System is not configured for HTTPS."}), 404
        
        try:
            # Send with correct mimetype for x509 certificates
            return send_file(
                ca_path,
                mimetype='application/pkix-cert',
                as_attachment=True,
                download_name='zentra_rootCA.crt'
            )
        except Exception as e:
            logger.error(f"[PKI] Certificate send error: {str(e)}")
            return jsonify({"error": "Unable to read the certificate file."}), 500
