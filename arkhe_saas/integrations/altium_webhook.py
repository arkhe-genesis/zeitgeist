import http.server
import socketserver
import json
import logging

PORT = 8000
logging.basicConfig(level=logging.INFO)

class WebhookHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/webhook/altium':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode('utf-8'))

                logging.info(f"Recebido webhook do Altium MCP. Payload: {payload}")

                # Mock para gerar PCB
                handover_id = payload.get("id")
                project_id = payload.get("projectId")
                coherence = payload.get("coherence")

                if handover_id and coherence > 0.90:
                    logging.info(f"Handover {handover_id} (Coerência {coherence}) aprovado.")
                    logging.info(f"Executando script de conversão Altium para projeto {project_id}...")
                    # Aqui integraria com a API real do Altium 365
                else:
                    logging.warning(f"Handover rejeitado ou dados inválidos: {payload}")

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'success', 'message': 'Webhook recebido'}).encode('utf-8'))
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Invalid JSON')
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    with socketserver.TCPServer(("", PORT), WebhookHandler) as httpd:
        logging.info(f"Servidor webhook rodando na porta {PORT}...")
        httpd.serve_forever()

if __name__ == '__main__':
    run_server()
