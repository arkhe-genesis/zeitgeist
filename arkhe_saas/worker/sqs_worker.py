import boto3
import json
import time
from jax_simulation import run_handover_simulation

sqs = boto3.client('sqs', region_name='us-east-1')
queue_url = 'https://sqs.us-east-1.amazonaws.com/123456789012/handover-queue'

def update_database(handover_id, result):
    print(f"Atualizando banco de dados para o handover: {handover_id} com resultado {result}")

def main():
    print("Iniciando Worker SQS...")
    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=10
            )
            for msg in response.get('Messages', []):
                body = json.loads(msg['Body'])
                handover_id = body['handoverId']

                # Executa simulação JAX + LLM
                result = run_handover_simulation(handover_id)

                # Atualiza banco de dados (PostgreSQL) com resultado
                update_database(handover_id, result)

                # Dispara novo evento SQS para downstream
                sqs.send_message(
                    QueueUrl=queue_url,
                    MessageBody=json.dumps({'type': 'HANDOVER_PROCESSED', 'handoverId': handover_id})
                )

                # Apaga mensagem recebida após processamento
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=msg['ReceiptHandle'])
                print(f"Mensagem {msg['MessageId']} processada e apagada.")

        except Exception as e:
            print(f"Erro ao processar mensagem do SQS: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
