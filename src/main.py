# from workflow import build_graph
import os
import json
from utils.logger import get_logger
import argparse
from callbacks.agent_metrics_handler import AgentMetricsHandler
from utils.global_state import set_global_state



if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=str, required=False, default="DevBench")
    parser.add_argument("--output_dir", type=str, required=False, default="gpt-5")
    args = parser.parse_args()
    dataset = args.dataset
    output_dir = args.output_dir

    os.makedirs(f'../outputs/{dataset}_outputs/{output_dir}', exist_ok=True)
    log_path = f'../outputs/{dataset}_outputs/{output_dir}/test_log.log'
    logger = get_logger(log_path)
    
    from workflow import build_graph

    app = build_graph()

    base_dir = '../datasets'
    dataset_dir = os.path.join(base_dir, dataset)
    
    repo_list = os.listdir(dataset_dir)
    try:
        repo_list.remove('.pytest_cache') 
        repo_list.remove('test_script.py') 
    except:
        pass
    repo_list.sort()

    for repo_name in repo_list:
        logger.info(f"Processing repository: {repo_name}")
        os.makedirs(f'../outputs/{dataset}_outputs/{output_dir}/{repo_name}/tmp_files', exist_ok=True)
        
        AgentMetricsHandler.set_global_log_file(os.path.expanduser(f"../outputs/{dataset}_outputs/{output_dir}/{repo_name}/tmp_files/agent_metrics.log"))
        repo_dir = os.path.join(dataset_dir, repo_name)
        repo_config = json.load(open(os.path.join(repo_dir, "config.json"), "r"))
        
        code_file_DAG = repo_config['code_file_DAG'] if 'code_file_DAG' in repo_config else []
        
        requirement = open(os.path.join(repo_dir, repo_config['PRD']), "r").read()
        if dataset == 'DevBench':
            uml_class = open(os.path.join(repo_dir, repo_config['UML_class']), "r").read()
            uml_sequence = open(os.path.join(repo_dir, repo_config['UML_sequence']), "r").read()
        if dataset == 'CodeProjectEval':
            for i in repo_config['UML']:
                if 'pyreverse' in i:
                    uml_class = open(os.path.join(repo_dir, i), "r").read()
                    break
            uml_sequence = ""
        arch_design = open(os.path.join(repo_dir, repo_config['architecture_design']), "r").read()

        initial_state = {
            "arch_steps": 0,
            "skeleton_steps": 0,
            "code_steps": 0,
            "dataset": dataset,
            "repo_name": repo_name, 
            "repo_dir": f'../outputs/{dataset}_outputs/{output_dir}/{repo_name}',
            "prd": requirement, 
            "uml_class": uml_class, 
            "uml_sequence": "", 
            "arch_design": arch_design, 
            "code_file_DAG": code_file_DAG, 
        }

        set_global_state(initial_state)

        final_state = app.invoke(initial_state)

        