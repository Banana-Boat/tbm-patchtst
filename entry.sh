if [ ! -d "./logs" ]; then
    mkdir ./logs
fi

timestamp=`date "+%m-%d_%H-%M-%S"`


# PatchTST模型 全部数据
python -u run_longExp.py \
      --data_path 20102631new.csv \
      --train_epochs 12 \
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
      | tee logs/PatchTST_ALL_${timestamp}.log

# PatchTST模型 仅俯仰角
#python -u run_longExp.py \
#      --data_path fuyangjiao6_1.csv \
#      --train_epochs 12 \
#      --model PatchTST \
#      --data custom \
#      --target 俯仰角\
#      --batch_size 64 \
#      --features S \
#      --seq_len 30 \
#      --label_len 15 \
#      --pred_len 30 \
#      --enc_in 1 \
#      --dec_in 1 \
#      --c_out 1 \
#      --random_seed 2023 \
#      --is_training 1 \
#      --root_path ./dataset/ \
#      --model_id patchtst \
#      --e_layers 2 \
#      --d_layers 1 \
#      --factor 3 \
#      --des 'Exp' \
#      --itr 1 \
#      | tee logs/PatchTST_fuyangjiao_${timestamp}.log
