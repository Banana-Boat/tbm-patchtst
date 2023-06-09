import utils.tools
from data_provider.data_factory import data_provider
from exp.exp_basic import Exp_Basic
from models import Informer, Autoformer, Transformer, DLinear, Linear, NLinear, PatchTST
from utils.tools import EarlyStopping, adjust_learning_rate, visual, test_params_flop, visualization
from utils.metrics import metric

import numpy as np
import torch
import torch.nn as nn
from torch import optim
from torch.optim import lr_scheduler

import os
import time

import warnings
import matplotlib.pyplot as plt
import numpy as np
import datetime

warnings.filterwarnings('ignore')


class Exp_Main(Exp_Basic):
  def __init__(self, args):
    super(Exp_Main, self).__init__(args)

  def _build_model(self):
    model_dict = {
      'Autoformer': Autoformer,
      'Transformer': Transformer,
      'Informer': Informer,
      'DLinear': DLinear,
      'NLinear': NLinear,
      'Linear': Linear,
      'PatchTST': PatchTST,
    }
    # 最后的.float()是将浮点参数和缓冲全部转换为浮点类型
    model = model_dict[self.args.model].Model(self.args).float()

    if self.args.use_multi_gpu and self.args.use_gpu:
      model = nn.DataParallel(model, device_ids=self.args.device_ids)
    return model

  def _get_data(self, flag):
    data_set, data_loader = data_provider(self.args, flag)
    return data_set, data_loader

  def _select_optimizer(self):
    model_optim = optim.Adam(self.model.parameters(), lr=self.args.learning_rate)
    return model_optim

  def _select_criterion(self):
    criterion = nn.MSELoss()
    return criterion

  def vali(self, vali_data, vali_loader, criterion):
    total_loss = []
    self.model.eval()  # 设置 model 为 eval 模式
    with torch.no_grad():  # 所有计算得出的tensor的requires_grad都自动设置为False，反向传播时就不会自动求导了，因此大大节约了显存或者说内存
      for i, (batch_x, batch_y, batch_x_mark, batch_y_mark) in enumerate(vali_loader):
        batch_x = batch_x.float().to(self.device)
        batch_y = batch_y.float()

        batch_x_mark = batch_x_mark.float().to(self.device)
        batch_y_mark = batch_y_mark.float().to(self.device)

        # decoder input
        dec_inp = torch.zeros_like(batch_y[:, -self.args.pred_len:, :]).float()
        dec_inp = torch.cat([batch_y[:, :self.args.label_len, :], dec_inp], dim=1).float().to(self.device)
        # encoder - decoder
        if self.args.use_amp:
          with torch.cuda.amp.autocast():
            if 'Linear' in self.args.model or 'TST' in self.args.model:
              outputs = self.model(batch_x)
            else:
              if self.args.output_attention:
                outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]
              else:
                outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)
        else:
          if 'Linear' in self.args.model or 'TST' in self.args.model:
            outputs = self.model(batch_x)
          else:
            if self.args.output_attention:
              outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]
            else:
              outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)
        f_dim = -1 if self.args.features == 'MS' else 0
        outputs = outputs[:, -self.args.pred_len:, f_dim:]
        batch_y = batch_y[:, -self.args.pred_len:, f_dim:].to(self.device)

        pred = outputs.detach().cpu()
        true = batch_y.detach().cpu()

        loss = criterion(pred, true)

        total_loss.append(loss)
    total_loss = np.average(total_loss)
    self.model.train()
    return total_loss

  def train(self, setting):
    train_data, train_loader = self._get_data(flag='train')
    vali_data, vali_loader = self._get_data(flag='val')
    test_data, test_loader = self._get_data(flag='test')

    path = os.path.join(self.args.checkpoints, setting)
    if not os.path.exists(path):
      os.makedirs(path)

    time_now = time.time()

    train_steps = len(train_loader)  # 实际返回的是 len(dataset) / batch_size
    early_stopping = EarlyStopping(patience=self.args.patience, verbose=True)

    model_optim = self._select_optimizer()
    criterion = self._select_criterion()

    if self.args.use_amp:
      scaler = torch.cuda.amp.GradScaler()

    # 使用one cycle的学习率调整策略（由args.lradj决定是否使用scheduler）
    scheduler = lr_scheduler.OneCycleLR(optimizer=model_optim,
                                        steps_per_epoch=train_steps,
                                        pct_start=self.args.pct_start,
                                        epochs=self.args.train_epochs,
                                        max_lr=self.args.learning_rate)

    for epoch in range(self.args.train_epochs):
      iter_count = 0
      train_loss = []

      self.model.train()  # 设置 model 为 train 模式
      epoch_time = time.time()
      for i, (batch_x, batch_y, batch_x_mark, batch_y_mark) in enumerate(train_loader):

        iter_count += 1  # 用于计算训练速度，每一百个batch统计一次速度
        model_optim.zero_grad()  # 每个batch在训练之前都需要做梯度清零

        batch_x = batch_x.float().to(self.device)
        batch_y = batch_y.float().to(self.device)
        batch_x_mark = batch_x_mark.float().to(self.device)
        batch_y_mark = batch_y_mark.float().to(self.device)

        # decoder input
        dec_inp = torch.zeros_like(batch_y[:, -self.args.pred_len:, :]).float()
        dec_inp = torch.cat([batch_y[:, :self.args.label_len, :], dec_inp], dim=1).float().to(self.device)

        # encoder - decoder
        if self.args.use_amp:
          with torch.cuda.amp.autocast():
            if 'Linear' in self.args.model or 'TST' in self.args.model:
              outputs = self.model(batch_x)
            else:
              if self.args.output_attention:
                outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]
              else:
                outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)

            f_dim = -1 if self.args.features == 'MS' else 0
            outputs = outputs[:, -self.args.pred_len:, f_dim:]
            batch_y = batch_y[:, -self.args.pred_len:, f_dim:].to(self.device)
            loss = criterion(outputs, batch_y)
            train_loss.append(loss.item())
        else:
          if 'Linear' in self.args.model or 'TST' in self.args.model:
            outputs = self.model(batch_x)
          else:
            if self.args.output_attention:
              outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]
            else:
              outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark, batch_y)

          f_dim = -1 if self.args.features == 'MS' else 0
          outputs = outputs[:, -self.args.pred_len:, f_dim:]
          batch_y = batch_y[:, -self.args.pred_len:, f_dim:].to(self.device)
          loss = criterion(outputs, batch_y)
          train_loss.append(loss.item())

        # 计算训练速度
        if (i + 1) % 40 == 0:
          print("\titers: {0}, epoch: {1} | loss: {2:.7f}".format(i + 1, epoch + 1, loss.item()))
          speed = (time.time() - time_now) / iter_count
          left_time = speed * ((self.args.train_epochs - epoch) * train_steps - i)
          print('\tspeed: {:.4f}s/iter; left time: {:.4f}s'.format(speed, left_time))
          iter_count = 0
          time_now = time.time()

        if self.args.use_amp:
          scaler.scale(loss).backward()
          scaler.step(model_optim)
          scaler.update()
        else:
          loss.backward()
          model_optim.step()

        if self.args.lradj == 'TST':
          adjust_learning_rate(model_optim, scheduler, epoch + 1, self.args, printout=False)
          scheduler.step()

      print("Epoch: {} cost time: {}".format(epoch + 1, time.time() - epoch_time))
      train_loss = np.average(train_loss)
      vali_loss = self.vali(vali_data, vali_loader, criterion)
      test_loss = self.vali(test_data, test_loader, criterion)
      print("Epoch: {0}, Steps: {1} | Train Loss: {2:.7f} Vali Loss: {3:.7f} Test Loss: {4:.7f}".format(
        epoch + 1, train_steps, train_loss, vali_loss, test_loss))

      # 保存模型(覆盖写)，如果vali_loss持续变大（次数超过patience）则停止训练
      early_stopping(vali_loss, self.model, path)
      if early_stopping.early_stop:
        print("Early stopping")
        break

      if self.args.lradj != 'TST':
        adjust_learning_rate(model_optim, scheduler, epoch + 1, self.args)
      else:
        print('Updating learning rate to {}'.format(scheduler.get_last_lr()[0]))

    best_model_path = path + '/' + 'checkpoint.pth'
    self.model.load_state_dict(torch.load(best_model_path))

    return self.model

  def test(self, setting, test=0):
    test_data, test_loader = self._get_data(flag='test')

    if test:
      print('loading model')
      # self.model.load_state_dict(torch.load(os.path.join('./checkpoints/03-13_17-39-52_PatchTST_custom_ftS_sl30_ll15_pl30_dm512_nh8_el2_dl1_df2048_fc3', 'checkpoint.pth')))
      self.model.load_state_dict(torch.load(os.path.join('./checkpoints/' + setting, 'checkpoint.pth')))

    # 用于评价指标的计算(metric)
    # preds = []
    # trues = []
    # inputx = []

    # 用于可视化反归一后的结果对比
    _preds = []
    _trues = []

    self.model.eval()
    with torch.no_grad():
      for i, (batch_x, batch_y, batch_x_mark, batch_y_mark) in enumerate(test_loader):
        batch_x = batch_x.float().to(self.device)
        batch_y = batch_y.float().to(self.device)

        batch_x_mark = batch_x_mark.float().to(self.device)
        batch_y_mark = batch_y_mark.float().to(self.device)

        # decoder input
        dec_inp = torch.zeros_like(batch_y[:, -self.args.pred_len:, :]).float()
        dec_inp = torch.cat([batch_y[:, :self.args.label_len, :], dec_inp], dim=1).float().to(self.device)
        # encoder - decoder
        if self.args.use_amp:
          with torch.cuda.amp.autocast():
            if 'Linear' in self.args.model or 'TST' in self.args.model:
              outputs = self.model(batch_x)
            else:
              if self.args.output_attention:
                outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]
              else:
                outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)
        else:
          if 'Linear' in self.args.model or 'TST' in self.args.model:
            outputs = self.model(batch_x)
          else:
            if self.args.output_attention:
              outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]
            else:
              outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)

        f_dim = -1 if self.args.features == 'MS' else 0
        outputs = outputs[:, -self.args.pred_len:, f_dim:]
        batch_y = batch_y[:, -self.args.pred_len:, f_dim:].to(self.device)
        outputs = outputs.detach().cpu().numpy()
        batch_y = batch_y.detach().cpu().numpy()

        # pred = outputs  # outputs.detach().cpu().numpy()  # .squeeze()
        # true = batch_y  # batch_y.detach().cpu().numpy()  # .squeeze()
        #
        # preds.append(pred)
        # trues.append(true)
        # inputx.append(batch_x.detach().cpu().numpy())

        _pred = []
        _true = []

        for index, batch in enumerate(outputs):
            _pred.append(batch[0, :])

        for index, batch in enumerate(batch_y):
            _true.append(batch[0, :])

        _preds += _pred
        _trues += _true

    # 反归一化
    preds_unnorm = test_data.inverse_transform((np.array(_preds)))
    trues_unnorm = test_data.inverse_transform((np.array(_trues)))

    mae, mse, rmse, mape, mspe, rse, corr, r2 = metric(preds_unnorm, trues_unnorm)
    print('mse:{}, mae:{}, rse:{}, r2:{}'.format(mse, mae, rse, r2))

    # 保存结果图
    folder_path = './results/' + setting + '/'
    if not os.path.exists(folder_path):
      os.makedirs(folder_path)

    visualization(folder_path, trues_unnorm, preds_unnorm, test_data.get_labels())

    if self.args.test_flop:
      test_params_flop((batch_x.shape[1], batch_x.shape[2]))
      exit()

    # preds = np.array(preds)
    # trues = np.array(trues)
    #
    # inputx = np.array(inputx)
    #
    # preds = preds.reshape(-1, preds.shape[-2], preds.shape[-1])
    # trues = trues.reshape(-1, trues.shape[-2], trues.shape[-1])
    # inputx = inputx.reshape(-1, inputx.shape[-2], inputx.shape[-1])

    # np.save(folder_path + 'metrics.npy', np.array([mae, mse, rmse, mape, mspe,rse, corr]))
    # np.save(folder_path + 'pred.npy', preds)
    # np.save(folder_path + 'true.npy', trues)
    # np.save(folder_path + 'x.npy', inputx)

    return

  def predict(self, setting, load=False):
    pred_data, pred_loader = self._get_data(flag='pred')

    if load:
      path = os.path.join(self.args.checkpoints, setting)
      best_model_path = path + '/' + 'checkpoint.pth'
      self.model.load_state_dict(torch.load(best_model_path))

    preds = []

    self.model.eval()
    with torch.no_grad():
      for i, (batch_x, batch_y, batch_x_mark, batch_y_mark) in enumerate(pred_loader):
        batch_x = batch_x.float().to(self.device)
        batch_y = batch_y.float()
        batch_x_mark = batch_x_mark.float().to(self.device)
        batch_y_mark = batch_y_mark.float().to(self.device)

        # decoder input
        dec_inp = torch.zeros([batch_y.shape[0], self.args.pred_len, batch_y.shape[2]]).float().to(batch_y.device)
        dec_inp = torch.cat([batch_y[:, :self.args.label_len, :], dec_inp], dim=1).float().to(self.device)
        # encoder - decoder
        if self.args.use_amp:
          with torch.cuda.amp.autocast():
            if 'Linear' in self.args.model or 'TST' in self.args.model:
              outputs = self.model(batch_x)
            else:
              if self.args.output_attention:
                outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]
              else:
                outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)
        else:
          if 'Linear' in self.args.model or 'TST' in self.args.model:
            outputs = self.model(batch_x)
          else:
            if self.args.output_attention:
              outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]
            else:
              outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)
        pred = outputs.detach().cpu().numpy()  # .squeeze()
        preds.append(pred)

    preds = np.array(preds)
    preds = preds.reshape(-1, preds.shape[-2], preds.shape[-1])

    # result save
    folder_path = './results/' + setting + '/'
    if not os.path.exists(folder_path):
      os.makedirs(folder_path)

    np.save(folder_path + 'real_prediction.npy', preds)

    return
