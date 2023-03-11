if [ ! -d "./logs" ]; then
    mkdir ./logs
fi

if [ ! -d "./logs/LongForecasting" ]; then
    mkdir ./logs/LongForecasting
fi

# PatchTST模型 ETTh1数据
#python -u run_longExp.py \
#      --random_seed 2023 \
#      --is_training 1 \
#      --root_path ./dataset/ \
#      --data_path ETTh1.csv \
#      --model_id ETTh1_336_96 \
#      --model PatchTST \
#      --data ETTh1 \
#      --features M \
#      --seq_len 336 \
#      --pred_len 96 \
#      --enc_in 7 \
#      --e_layers 3 \
#      --n_heads 4 \
#      --d_model 16 \
#      --d_ff 128 \
#      --dropout 0.3\
#      --fc_dropout 0.3\
#      --head_dropout 0\
#      --patch_len 16\
#      --stride 8\
#      --des 'Exp' \
#      --train_epochs 3\
#      --itr 1 --batch_size 128 --learning_rate 0.0001 >logs/LongForecasting/PatchTST_ETTh1_336_96.log \

# Transformer模型 ETTh1数据
#python -u run_longExp.py \
#      --random_seed 2023 \
#      --is_training 1 \
#      --root_path ./dataset/ \
#      --data_path ETTh1.csv \
#      --model_id ETTh1_96_96 \
#      --model Transformer \
#      --data ETTh1 \
#      --features M \
#      --seq_len 96 \
#      --label_len 48 \
#      --pred_len 96 \
#      --e_layers 2 \
#      --d_layers 1 \
#      --factor 3 \
#      --enc_in 7 \
#      --dec_in 7 \
#      --c_out 7 \
#      --des 'Exp' \
#      --itr 1  >logs/LongForecasting/Transformer'_Etth1_'96.log

# Transformer模型 盾构机数据
#python -u run_longExp.py \
#      --random_seed 2023 \
#      --is_training 1 \
#      --train_epochs 3 \
#      --root_path ./dataset/ \
#      --data_path 20102631new.csv \
#      --model_id 20102631new_96_96 \
#      --model Transformer \
#      --data custom \
#      --target 俯仰角\
#      --features M \
#      --seq_len 96 \
#      --label_len 48 \
#      --pred_len 96 \
#      --e_layers 2 \
#      --d_layers 1 \
#      --factor 3 \
#      --enc_in 31 \
#      --dec_in 31 \
#      --c_out 31 \
#      --des 'Exp' \
#      --itr 1  >logs/LongForecasting/Transformer'_20102631new_'96.log


# PatchTST模型 盾构机数据
python -u run_longExp.py \
      --random_seed 2023 \
      --is_training 1 \
      --train_epochs 3 \
      --root_path ./dataset/ \
      --data_path 20102631new.csv \
      --model_id 20102631new_96_96 \
      --model PatchTST \
      --data custom \
      --target 俯仰角\
      --batch_size 64 \
      --features M \
      --seq_len 30 \
      --label_len 15 \
      --pred_len 30 \
      --e_layers 2 \
      --d_layers 1 \
      --factor 3 \
      --enc_in 31 \
      --dec_in 31 \
      --c_out 31 \
      --des 'Exp' \
      --itr 1 \
      | tee logs/LongForecasting/PatchTST'_20102631new_'96.log
