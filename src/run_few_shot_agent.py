
import os
from data_interface import DataLoader
from utils.utils import load_json
from langchain.chat_models import ChatOpenAI
from agents.zero_shot import ZeroShotAgent
from config import config, api_key
import wandb
import langchain
langchain.verbose = False

# If you don't want your script to sync to the cloud
# os.environ["WANDB_MODE"] = "offline"

def main():
    
    wandb.init(
        project=config.project,
        config=config,
        name= config.current_experiment,
        entity=config.entity
    )

    artifact = wandb.Artifact('query_results', type='dataset')
    table = wandb.Table(columns=["Question", "Gold Query", "Predicted Query", "Success"])    

    wandb.define_metric("predicted_sql_execution_time", summary="mean")
    wandb.define_metric("gold_sql_execution_time", summary="mean")

    llm = ChatOpenAI(
        openai_api_key=api_key, 
        model_name=config.llm_settings.model,
        temperature=config.llm_settings.temperature,
        request_timeout=config.llm_settings.request_timeout
    )

    data_loader     = DataLoader()    
    zero_shot_agent = ZeroShotAgent(llm)
    
    no_questions = len(data_loader.get_questions())
    score = 0
    accuracy = 0
    for i, row in enumerate(data_loader.get_questions()):  
           
        # if i == 5 or i == 26 or i == 27:
        #     continue
        golden_sql = row['SQL']
        db_id = row['db_id']            
        print('db_id: ', db_id)
        question = row['question']
        evidence = row['evidence']
        difficulty = row['difficulty']

        sql_schema = data_loader.get_schema_and_sample_data(db_id)
        predicted_sql = zero_shot_agent.generate_query(sql_schema, question, evidence)        
        success = data_loader.execute_queries_and_match_data(predicted_sql, golden_sql, db_id)

        score += success
        if i > 0: accuracy = score / i

        table.add_data(question, golden_sql, predicted_sql, success)
        wandb.log({
            "accuracy": accuracy,
            "total_tokens": zero_shot_agent.total_tokens,
            "prompt_tokens": zero_shot_agent.prompt_tokens,
            "completion_tokens": zero_shot_agent.completion_tokens,
            "total_cost": zero_shot_agent.total_cost,
            "difficulty": difficulty,
            "openAPI_call_execution_time": zero_shot_agent.last_call_execution_time,
            "predicted_sql_execution_time": data_loader.last_predicted_execution_time,
            "gold_sql_execution_time": data_loader.last_gold_execution_time
        }, step=i+1)
    
        print("Percentage done: ", round(i / no_questions * 100, 2), "% Domain: ", 
              db_id, " Success: ", success, " Accuracy: ", accuracy)
        
    
    wandb.run.summary['number_of_questions']                = no_questions
    wandb.run.summary["accuracy"]                           = accuracy
    wandb.run.summary["total_tokens"]                       = zero_shot_agent.total_tokens
    wandb.run.summary["prompt_tokens"]                      = zero_shot_agent.prompt_tokens
    wandb.run.summary["completion_tokens"]                  = zero_shot_agent.completion_tokens
    wandb.run.summary["total_cost"]                         = zero_shot_agent.total_cost
    wandb.run.summary['total_predicted_execution_time']     = data_loader.total_predicted_execution_time
    wandb.run.summary['total_gold_execution_time']          = data_loader.total_gold_execution_time
    wandb.run.summary['total_openAPI_execution_time']       = zero_shot_agent.total_call_execution_time


    artifact.add(table, "query_results")
    wandb.log_artifact(artifact)

    artifact_code = wandb.Artifact('code', type='code')
    artifact_code.add_file("src/agents/zero_shot.py")
    wandb.log_artifact(artifact_code)

    wandb.finish()



if __name__ == "__main__":
    main()