import os
from datasets import get_dataset
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.callbacks import get_openai_callback
from utils.timer import Timer
import logging


from config import api_key, load_config
import wandb
import langchain
# langchain.verbose = True

# If you don't want your script to sync to the cloud
os.environ["WANDB_MODE"] = "offline"

CLASSIFIY_PROMPT = """
You are a text-to-SQL expert able to identify poorly formulated questions in natural language.
This instruction is regarding text-to-SQL generation, or in other words converting natural language questions into SQL queries using LLMs. 
The dataset used is consisting of questions and their corresponding golden SQL queries. You will be given the database schema of the database corresponding to the question.
Furthermore, you will also be given a hint that provides information that is needed to correctly convert the question and interpret the database schema.  
However, some of the questions in the data are poorly formulated or contain errors. 

Below is a classification scheme for the questions that are to be converted into SQL queries. 

0 = Correct question. May still contain minor errors in language or minor ambiguities that do not affect the interpretation and generation of the SQL query
1 = Is unclear, ambiguous, unspecific or contain grammatical errors that surely is going to affect the interpretation and generation of the SQL query
1 = The question is wrongly formulated when considering the structure of the database schema. The information that the question is asking for is not possible to accurately retrieve from the database.
1 = The question is unspecific in which columns that are to be returned. The question is not asking for a specific column, but asks generally about a table in the database.

Here are some examples of questions that would be classified with 1 and an explanation of why:

Example: List the customer who made the transaction id : 3682978
Explanation: The question is unspecific in which columns that are to be returned. It asks to list the customers, but does not specify which columns that are to be returned from the client table. 

Example: Which district has the largest amount of female clients?
Explanation: The question is unspecific in which columns that are to be returned. It asks "which district", but does not specify which columns that are to be returned from the district table. 

Database schema: 

{database_schema}

Hint:
{evidence}

Please classify the question below according to the classification scheme above.

Do not return anything else than the mark as a sole number. Do not return any corresponding text or explanations.

Question: {question}
"""

#1 = Gray area, minor errors that may or may not affect the interpretation and generation of the SQL query.

class Classifier():
    
    total_tokens = 0
    prompt_tokens = 0 
    total_cost = 0
    completion_tokens = 0
    last_call_execution_time = 0
    total_call_execution_time = 0

    def __init__(self, llm):        
        self.llm = llm

        self.prompt_template = CLASSIFIY_PROMPT
        prompt = PromptTemplate(    
            # input_variables=["question", "database_schema","evidence"],
            input_variables=["question", "database_schema", "evidence"],
            template=CLASSIFIY_PROMPT,
        )

        self.chain = LLMChain(llm=llm, prompt=prompt)


    def classify_question(self, question, schema, evidence):
        with get_openai_callback() as cb:
            with Timer() as t:
                response = self.chain.run({
                    'question': question,
                    'database_schema': schema,
                    'evidence': evidence,
                })

            logging.info(f"OpenAI API execution time: {t.elapsed_time:.2f}")
            
            self.last_call_execution_time = t.elapsed_time
            self.total_call_execution_time += t.elapsed_time
            self.total_tokens += cb.total_tokens
            self.prompt_tokens += cb.prompt_tokens
            self.total_cost += cb.total_cost
            self.completion_tokens += cb.completion_tokens

            return response


accepted_faults = [1, 3]

def main():
    config = load_config("classifier_config.yaml")

    wandb.init(
        project=config.project,
        config=config,
        name=config.current_experiment,
        entity=config.entity
    )

    artifact = wandb.Artifact('query_results', type='dataset')
    table = wandb.Table(columns=["Question", "Classified_quality", "Difficulty"]) ## Är det något mer vi vill ha med här?

    llm = ChatOpenAI(
        openai_api_key=api_key, 
        model_name=config.llm_settings.model,
        temperature=config.llm_settings.temperature,
        request_timeout=config.llm_settings.request_timeout
    )

    dataset = get_dataset("BIRDCorrectedFinancialGoldAnnotated")
    classifier = Classifier(llm)

    wandb.config['prompt'] = classifier.prompt_template

    no_data_points = dataset.get_number_of_data_points()

    tp = 0
    fp = 0
    tn = 0
    fn = 0
    
    for i in range(no_data_points):
        data_point = dataset.get_data_point(i)
        evidence = data_point['evidence']
        db_id = data_point['db_id']            
        question = data_point['question']
        difficulty = data_point['difficulty'] if 'difficulty' in data_point else ""
        annotated_question_quality = data_point["annotation"]
        
        sql_schema = dataset.get_schema_and_sample_data(db_id)

        classified_quality = classifier.classify_question(question, sql_schema, evidence)

        annotated_question_qualities = set(annotated_question_quality)
        if classified_quality.isdigit() and int(classified_quality) == 1:            
            if any(element in annotated_question_qualities for element in accepted_faults):
                tp += 1
            else:
                fp += 1
        elif classified_quality.isdigit() and int(classified_quality) == 0:
            if any(element in annotated_question_qualities for element in accepted_faults):
                fn += 1
            else:
                tn += 1
        
        table.add_data(question, classified_quality, difficulty)
        wandb.log({                      
            "total_tokens": classifier.total_tokens,
            "prompt_tokens": classifier.prompt_tokens,
            "completion_tokens": classifier.completion_tokens,
            "total_cost": classifier.total_cost,
            "openAPI_call_execution_time": classifier.last_call_execution_time,
        }, step=i+1)
    
        print("Predicted quality: ", classified_quality, " Annotated quality: ", " ".join(map(str, annotated_question_quality)))
        
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    f1 = 2 * ((precision * recall) / (precision + recall))
    accuracy = tp + tn / (tp + tn + fp + fn)

    wandb.run.summary['accuracy']                           = accuracy
    wandb.run.summary['precision']                          = precision
    wandb.run.summary['recall']                             = recall
    wandb.run.summary['f1']                                 = f1
    wandb.run.summary["total_tokens"]                       = classifier.total_tokens
    wandb.run.summary["prompt_tokens"]                      = classifier.prompt_tokens
    wandb.run.summary["completion_tokens"]                  = classifier.completion_tokens
    wandb.run.summary["total_cost"]                         = classifier.total_cost
    wandb.run.summary['total_predicted_execution_time']     = dataset.total_predicted_execution_time
    wandb.run.summary['total_openAPI_execution_time']       = classifier.total_call_execution_time

    artifact.add(table, "query_results")
    wandb.log_artifact(artifact)

    artifact_code = wandb.Artifact('code', type='code')
    artifact_code.add_file("src/run_classifier.py")
    wandb.log_artifact(artifact_code)

    wandb.finish()



if __name__ == "__main__":
    main()