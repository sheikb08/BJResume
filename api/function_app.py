import os
import json
import logging

import azure.functions as func
from azure.core.exceptions import ResourceNotFoundError
from azure.core.credentials import AzureNamedKeyCredential
from azure.data.tables import TableServiceClient, UpdateMode

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="GetResumeCounter", methods=["GET"])
def get_resume_counter(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing resume counter request.")

    try:
        account_name = os.getenv("COSMOS_ACCOUNT_NAME")
        account_key = os.getenv("COSMOS_ACCOUNT_KEY")
        table_endpoint = os.getenv("COSMOS_TABLE_ENDPOINT")
        table_name = os.getenv("COSMOS_TABLE_NAME", "ResumeCounter")

        if not account_name or not account_key or not table_endpoint:
            return func.HttpResponse(
                json.dumps({"error": "Missing Cosmos DB settings"}),
                status_code=500,
                mimetype="application/json"
            )

        credential = AzureNamedKeyCredential(account_name, account_key)
        service = TableServiceClient(endpoint=table_endpoint, credential=credential)
        table_client = service.get_table_client(table_name=table_name)

        partition_key = "resume"
        row_key = "visitorcount"

        try:
            entity = table_client.get_entity(partition_key=partition_key, row_key=row_key)
            current_count = int(entity.get("Count", 0))
        except ResourceNotFoundError:
            entity = {
                "PartitionKey": partition_key,
                "RowKey": row_key,
                "Count": 0
            }
            current_count = 0

        entity["Count"] = current_count + 1

        table_client.upsert_entity(entity=entity, mode=UpdateMode.MERGE)

        return func.HttpResponse(
            json.dumps({"count": entity["Count"]}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as ex:
        logging.exception("Error processing resume counter.")
        return func.HttpResponse(
            json.dumps({"error": str(ex)}),
            status_code=500,
            mimetype="application/json"
        )
