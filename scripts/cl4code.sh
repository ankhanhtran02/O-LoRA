#!/bin/bash
set -x

# bash scripts/cl4code.sh> logs_and_outputs/cl4code/logs/train_and_infer.log 2>&1 &

TASK_LIST=(
   "CONCODE"
   "CodeTrans"
   "CodeSearchNet"
   "BFP"
   "KodCode"
   "RunBugRun"
   "TheVault_Csharp"
   "CoST"
)

declare -A MAX_TARGET_LENGTH=(
   [CodeTrans]=256
   [CodeSearchNet]=256
   [BFP]=256
   [CONCODE]=256
   [KodCode]=150
   [RunBugRun]=150
   [CoST]=150
   [TheVault_Csharp]=150
)

for i in "${!TASK_LIST[@]}"; do
   task="${TASK_LIST[$i]}"
   index=$((i + 1))

   python3 src/run_uie_lora.py \
      --do_train \
      --do_predict \
      --predict_with_generate \
      --model_name_or_path Salesforce/codet5-large \
      --model_revision 4ca0fb4dc19d81c35a7dffe4356d8a6236a687b4 \
      --data_dir CL_Benchmark \
      --task "${task}" \
      --output_dir "logs_and_outputs/cl4code/outputs/${index}-${task}" \
      --per_device_train_batch_size 8 \
      --per_device_eval_batch_size 16 \
      --gradient_accumulation_steps 4 \
      --learning_rate 1e-04 \
      --num_train_epochs 3 \
      --run_name "olora_${task}" \
      --add_task_name False \
      --add_dataset_name False \
      --generation_max_length "${MAX_TARGET_LENGTH[$task]}" \
      --overwrite_output_dir \
      --overwrite_cache \
      --lr_scheduler_type constant \
      --warmup_steps 0 \
      --logging_strategy steps \
      --logging_steps 10 \
      --evaluation_strategy epoch \
      --save_strategy no \
      --lamda_1 0.5 \
      --lamda_2 0

   sleep 5
done
