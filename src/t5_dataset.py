import pandas as pd
import numpy as np
import hashlib

from typing import Dict
from datasets import load_dataset
import json

from task_info import TASK_SPECS, HF_SPLIT_MAP, INSTRUCTION_POOL, TRAIN_ONLY_TASKS, TASK_LIST, INSTRUCTION_SPLIT_POLICY, DATASET_TO_TASK

"""
(check) find official dataset and their exact collumn name
""" 
class T5Dataset:
    def __init__(self, tokenizer, task):
        """
        Dataset class for T5 model experiments.
        Args:
            task (str): Name of the downstream task.
            tokenizer (HuggingFace Tokenizer): T5 model tokenizer to use.
        """
        
        self.tokenizer = tokenizer
        self.task = task
        self.task_list = ['CodeTrans', 
                        'CodeSearchNet',
                        'BFP', 
                        'CONCODE',
                        'TheVault_Csharp',
                        'KodCode',
                        'RunBugRun',
                        'CoST']
        
        self.text_key = {'CONCODE': 'nl',
                           'CodeTrans': 'java',
                           'CodeSearchNet': 'code_tokens',   
                           'BFP': 'buggy',
                           'TheVault_Csharp': 'code',      
                           'KodCode': 'question',           
                           'RunBugRun': 'buggy_code',
                           'CoST': 'lang1'}               
        self.label_key = {'CONCODE': 'code',
                            'CodeTrans': 'cs',
                            'CodeSearchNet': 'docstring_tokens',
                            'BFP': 'fixed',
                            'TheVault_Csharp': 'docstring',    
                            'KodCode': 'solution',                
                            'RunBugRun': 'fixed_code',
                            'CoST': 'lang2'}              
        
        self.max_input_length = {'CodeTrans': 320,
                                 'CodeSearchNet': 256,
                                 'BFP': 130,
                                 'CONCODE': 320,
                                 'TheVault_Csharp': 256,        # TODO: update if needed
                                 'KodCode': 256,                 # TODO: update if needed
                                 'RunBugRun': 256,
                                 'CoST': 256}               # TODO: update if needed

        self.train_only_tasks = {
            'KodCode': {'val': 5000, 'test': 5000},
            'RunBugRun': {'val': 972,  'test': 1000},
        }


    def _split_train_only(self, dataset, task, split, split_seed=42):

        sizes = self.train_only_tasks[task]
        test_size  = sizes['test']
        val_size   = sizes['val']

        # Step 1: carve out test from the full dataset
        tmp = dataset.train_test_split(test_size=test_size, seed=split_seed)
        test_ds = tmp['test']

        # Step 2: carve out val from the remainder (test never included)
        tmp2 = tmp['train'].train_test_split(test_size=val_size, seed=split_seed)
        train_ds = tmp2['train']
        val_ds   = tmp2['test']

        mapping = {'train': train_ds, 'validation': val_ds, 'test': test_ds}
        if split not in mapping:
            raise ValueError(f"Unknown split '{split}' for train-only task '{task}'")
        return mapping[split]


    def select_subset_ds(self, ds, k=2000, seed=0):
        np.random.seed(seed)
        num_samples = min(k, ds.shape[0])
        idx_total = np.random.choice(np.arange(ds.shape[0]), num_samples, replace=False)
        return ds.select(idx_total)

    @staticmethod
    def _to_string(value):
        if value is None:
            return ""
        return str(value)

    def _get_candidate_instruction_pool(self, task, split_name):
        task_type = TASK_SPECS[task]['task_type']
        pool = INSTRUCTION_POOL.get(task_type, [])
        if not pool:
            raise ValueError(f"No instruction templates defined for task_type '{task_type}'")

        policy = INSTRUCTION_SPLIT_POLICY.get(split_name, INSTRUCTION_SPLIT_POLICY['train'])
        if policy['pool_scope'] == 'full':
            return pool

        if policy['pool_scope'] == 'head_fraction':
            fraction = float(policy.get('fraction', 0.75))
            if fraction <= 0:
                raise ValueError(f"Invalid fraction {fraction} for split '{split_name}'")
            head_size = max(1, int(len(pool) * fraction))
            return pool[:head_size]

        raise ValueError(f"Unknown pool_scope '{policy['pool_scope']}' for split '{split_name}'")

    def _select_instruction_template(self, task, sample_key, split_name, split_seed):
        candidate_pool = self._get_candidate_instruction_pool(task, split_name)
        random_key = f"{split_seed}::{split_name}::{sample_key}"
        idx = int(hashlib.md5(random_key.encode("utf-8")).hexdigest(), 16) % len(candidate_pool)
        return candidate_pool[idx]

    def _render_instruction(self, task, raw_input, sample_key, split_name, split_seed):
        spec = TASK_SPECS[task]
        template = self._select_instruction_template(task, sample_key, split_name, split_seed)

        format_values: Dict[str, str] = {
            'language': spec.get('language', 'code'),
            'description': raw_input,
            'code': raw_input,
            'source_lang': spec.get('source_lang', spec.get('language', 'source language')),
            'target_lang': spec.get('target_lang', 'target language'),
        }
        return template.format(**format_values)

    # Function to preprocess raw input & label text into tokenized dictionary
    def preprocess_function(self, 
                            examples, 
                            task,
                            max_length=512,
                            max_input_length=None,
                            split_name='train',
                            split_seed=42,
                            #batched=False
                            ):
        if task not in self.task_list:
            raise ValueError(f"Unknown task name: {task}")

        if split_name == 'validation':
            subset = 'dev'
        else:
            subset = split_name

        dict_final = {"Task": DATASET_TO_TASK.get(task, task), "Dataset": task, "Samples": [], "subset": subset} 

        dict_final['Instance'] = {
            'id': examples['id'],
            'sentence': examples['input'],
            'label': examples['output'],
            'ground_truth': examples['output'],
            'instruction': "{0}"
        }
        return dict_final

    def get_final_ds(self, 
                     data_size_dict,
                     seed=0):
        """Function that returns final T5 dataloader.
        Args:
            task (str): Name of the downstream task.
            split (str): Which data split to use (train/validation/test).
            batch_size (int): Batch size to use in the dataloader.
            k (int, optional): Number of samples to use for each class. Defaults to -1, not sub-sample the data.
            seed (int, optional): Seed used for random shuffle. Defaults to 0.
            target_len (int, optional): Length of the model output (in tokens). Defaults to 2.
            max_length (int, optional): Length of the model input (in tokens). Defaults to 512.

            
        Returns:
            Dataloader: Torch Dataloader with preprocessed input text & label.
        """
        task = self.task
        splits = ['train', 'validation', 'test']
        datasets_dict = {}
        for split in splits:
            ds = load_dataset(
                "dongg18/CODETASK_with_instruction_pool",
                data_files={split: f"{task}/{split}-*.parquet"},
                split=split,
            )
            datasets_dict[split] = ds

        for split, dataset in datasets_dict.items():
            dataset = dataset.remove_columns([c for c in dataset.column_names if c not in ('id', 'input', 'output')])

            k = data_size_dict[split]
            # Selecting k subset of the samples (if requested)
            if k != -1:
                dataset = self.select_subset_ds(dataset, k=k)
            else:
                dataset = dataset.shuffle(seed=seed)
            

            dataset = dataset.map(
                lambda x: self.preprocess_function(x,
                                                task,
                                                max_length=None,
                                                max_input_length=None,
                                                split_name=split,
                                                split_seed=seed,
                                                ),
                batched=False,
                remove_columns=dataset.column_names
            )
            datasets_dict[split] = dataset

        return datasets_dict

if __name__ == "__main__":
    tokenizer = None
    dataset = T5Dataset(tokenizer, 'CodeSearchNet')
    data_size_dict = {'train': -1, 'validation': -1, 'test': -1}
    final_ds = dataset.get_final_ds(data_size_dict)
    print(final_ds['train'])
    print(final_ds['validation'])
    print(final_ds['test'])
    print(json.dumps(final_ds['validation'][0], indent=2))