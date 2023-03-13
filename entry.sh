if [ ! -d "./logs" ]; then
    mkdir ./logs
fi

timestamp=`date "+%m-%d_%H-%M-%S"`

# Transformer模型 盾构机数据
#python -u run_longExp.py \
#       --data_path 20102631new.csv \
#       --train_epochs 15 \
#       --model Transformer \
#       --data custom \
#       --target 俯仰角\
#       --batch_size 64 \
#       --features M \
#       --seq_len 30 \
#       --label_len 15 \
#       --pred_len 30 \
#       --enc_in 31 \
#       --dec_in 31 \
#       --c_out 31 \
#       --random_seed 2023 \
#       --is_training 1 \
#       --root_path ./dataset/ \
#       --model_id transformer \
#       --e_layers 2 \
#       --d_layers 1 \
#       --factor 3 \
#       --des 'Exp' \
#       --itr 1 \
#       | tee logs/Transformer_${timestamp}.log


# PatchTST模型 盾构机数据
python -u run_longExp.py \
      --data_path 20102631new.csv \
      --train_epochs 15 \
      --model PatchTST \
      --data custom \
      --target 俯仰角\
      --batch_size 64 \
      --features M \
      --seq_len 30 \
      --label_len 15 \
      --pred_len 30 \
      --enc_in 31 \
      --dec_in 31 \
      --c_out 31 \
      --random_seed 2023 \
      --is_training 1 \
      --root_path ./dataset/ \
      --model_id patchtst \
      --e_layers 2 \
      --d_layers 1 \
      --factor 3 \
      --des 'Exp' \
      --itr 1 \
      | tee logs/PatchTST_${timestamp}.log
