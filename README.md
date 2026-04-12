# O-LoRA

- This repo releases our implementation for the O-LoRA model.
- It is built based on the pretrained T5-large model, and finetuned on our data.

![image_text](https://github.com/cmnfriend/O-LoRA/blob/main/data/O-LoRA.jpg)


## Setup

You can install the required libraries by running 

```
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```


## Training and Evaluation

For t5-large:

order1:

```
bash scripts/cl4code.sh> logs_and_outputs/cl4code/logs/train_and_infer.log 2>&1 &
```


## Citation
```latex
@article{wang2023orthogonal,
  title={Orthogonal Subspace Learning for Language Model Continual Learning},
  author={Wang, Xiao and Chen, Tianze and Ge, Qiming and Xia, Han and Bao, Rong and Zheng, Rui and Zhang, Qi and Gui, Tao and Huang, Xuanjing},
  journal={arXiv preprint arXiv:2310.14152},
  year={2023}
}
```


