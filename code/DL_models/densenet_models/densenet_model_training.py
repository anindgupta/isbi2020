#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep  9 19:53:05 2019

@author: anindya
"""
import os
import pandas as pd
from DL_models.densenet_models.densenet_losses import categorical_focal_loss, f1,b_f_loss  # ,binary_focal_loss
from DL_models.densenet_models.densenet_like_non_temporal import densenet_like_non_temporal
from DL_models.densenet_models.densenet_imagenet_non_temporal import densenet_imagenet_non_temporal
from keras.metrics import logcosh, mean_absolute_error
from keras import optimizers
from keras.callbacks import CSVLogger, EarlyStopping
from DL_models.batch_iterator import batch_iterator_non_temporal

function_mappings = {
    "densenet_like_non_temporal": densenet_like_non_temporal,
    "densenet_imagenet_non_temporal": densenet_imagenet_non_temporal
}


def make_dir(dir_name):
    os.makedirs(os.getcwd() + "/" + dir_name, exist_ok=True)  #
    return dir_name

class model_training:
    
    def densenet_training(
        data,
        nb_train_samples,
        val_data,
        nb_validation_samples,
        epoch,
        batch,
        i,
        img_row,
        img_col,
        channel,
        final_ac_regression,
        dense_blocks,
        dense_layers,
        growth_rate,
        bottleneck,
        compression,
        block_depth,
        model_name,
        trained_models,
        log_files,
        dropout_rate_flag,
        no_of_nodes,
        batch_norm_flag,
        regression,
        early_stopping,
    ):
        print(model_name + " model is ready for training")
        pred_activation = final_ac_regression
        if regression:
            model_type = "regression"

            loss = [b_f_loss(gamma=2.0, alpha=1)]#[logcosh]
            metrics = ["mean_absolute_error"]
        else:
            model_type = "class"
            loss = [categorical_focal_loss(gamma=2.0, alpha=1)]
            metrics = ["acc", "categorical_accuracy", f1]

        # model-1
        if model_name == "densenet_like_non_temporal":
            NET = function_mappings[model_name](
                img_row=img_row,
                img_col=img_col,
                channel=channel,
                dense_blocks=dense_blocks,
                dense_layers=dense_layers,
                growth_rate=growth_rate,
                nb_classes=no_of_nodes,
                dropout_rate=dropout_rate_flag,
                bottleneck=bottleneck,
                compression=compression,
                weight_decay=1e-4,
                depth=block_depth,
                model_type=model_type,
                pred_activation=pred_activation
            )            
        # model-2
        if model_name == "densenet_imagenet_non_temporal":
            NET = function_mappings[model_name](
                img_rows=img_row,
                img_cols=img_col,
                channel=channel,
                no_of_nodes=no_of_nodes,
                pred_activation=pred_activation,
                model_type=model_type,
                dropout_rate=dropout_rate_flag,
            )            

        learning_rate = 1e-5  # 0.01#2e-5
        #decay_rate = learning_rate / epoch
        rms = optimizers.adam(learning_rate=0.002, beta_1=0.9, beta_2=0.999)#(lr=learning_rate)#,
        NET.compile(loss=loss, optimizer=rms, metrics=metrics)
        if i == 0:
            NET.summary()
        csv_logger = CSVLogger(
            os.getcwd()
            + "/"
            + log_files
            + str(model_name)
            + "_"
            + str(model_type)
            + "_"
            + str(i + 1)
            + ".csv",
            append=True,
            separator=",",
        )

        if early_stopping:
            early_stopping = EarlyStopping(monitor="val_loss", patience=5)
            callbacks = [csv_logger, early_stopping]
        else:
            callbacks = [csv_logger]
        NET.fit_generator(
            data,
            verbose=1,
            validation_data=val_data,
            steps_per_epoch=nb_train_samples / batch,
            epochs=epoch,  # class_weight=weights,
            callbacks=callbacks,
            validation_steps=nb_validation_samples / batch,
        )
        NET.save(
            os.getcwd()
            + "/"
            + trained_models
            + str(model_name)
            + "_"
            + str(model_type)
            + "_"
            + str(i + 1)
            + ".h5"
        )
        NET.save_weights(
            os.getcwd()
            + "/"
            + trained_models
            + str(model_name)
            + "_"
            + str(model_type)
            + "_weights_"
            + str(i + 1)
            + ".h5"
        )
        del NET
        import gc

        gc.collect()

    def _model_training(
        models="model_name",
        img_row=120,
        img_col=120,
        channel=3,
        final_ac_regression='sigmoid',
        dense_blocks=4,
        dense_layers=-1,
        growth_rate=12,
        bottleneck=False,
        compression=1.0,
        block_depth=40,
        batch=32,
        epoch=5,
        final_layer_no_of_nodes=3,
        regression_flag=True,
        dropout_rate_flag=True,
        batch_norm_flag=True,
        early_stopping=True,
        five_fold_flag=True,

    ):
        import os
        import os.path

        data_folder_path = os.getcwd()
        # for model_type in range(len(models)):

        results_dir = make_dir("results/non_temporal")
        fold_path = (
            data_folder_path + "/train_cv_non_temporal_data/"
        )  # _non_temporal/"
        dir_path = make_dir(results_dir + "/" + models) + "/"
        mode = models

        log_files_save_path = make_dir(dir_path + "logs") + "/"
        trained_models_save_path = make_dir(dir_path + "trained_models") + "/"

        if models.split("_")[0] == "densenet":
            from keras.applications.densenet import preprocess_input

        no_of_folds = 1
        if five_fold_flag:
            no_of_folds = 3#5
        for i in range(no_of_folds):  #
            print(
                "\n" + "non-temporal cross-validation..." + str(i + 1) + "\n",
                flush=True,
            )
            f_tr = fold_path + "fold_train_" + str(i + 1) + ".xlsx"
            f_val = fold_path + "fold_val_" + str(i + 1) + ".xlsx"
            tmp = pd.read_excel(f_tr)
            tmp1 = pd.read_excel(f_val)

            # ===== data generator===============#

            print("\n" + "Starting training..." + "\n")

            tr_data = batch_iterator_non_temporal(
                f_tr,
                img_row,
                img_col,
                channel,
                batch,
                model_name=mode,
                regression=regression_flag,
                preprocess_input=preprocess_input,
            )

            val_data = batch_iterator_non_temporal(
                f_val,
                img_row,
                img_col,
                channel,
                batch,
                model_name=mode,
                regression=regression_flag,
                preprocess_input=preprocess_input,
            )
            nb_train_samples = round(len(tmp))  # *1.2)#24000#00
            nb_validation_samples = round(len(tmp1) * 1.2)  # *2#840#00

            single_frame_model_path = None
            single_frame_weights_path = None
            if mode == "densenet_sing_frm_finetune_temporal":
                single_frame_model_path = single_frame_model_path
                single_frame_weights_path = single_frame_weights_path

            Net = model_training.densenet_training(
                data=tr_data,
                nb_train_samples=nb_train_samples,
                val_data=val_data,
                nb_validation_samples=nb_validation_samples,
                epoch=epoch,
                batch=batch,
                i=i,
                img_row=img_row,
                img_col=img_col,
                channel=channel,
                final_ac_regression=final_ac_regression,
                dense_blocks=dense_blocks,
                dense_layers=dense_layers,
                growth_rate=growth_rate,
                bottleneck=bottleneck,
                compression=compression,
                block_depth=block_depth,
                model_name=mode,
                trained_models=trained_models_save_path,
                log_files=log_files_save_path,
                dropout_rate_flag=dropout_rate_flag,
                no_of_nodes=final_layer_no_of_nodes,
                batch_norm_flag=batch_norm_flag,
                regression=regression_flag,
                early_stopping=early_stopping,
            )

            print(
                "\n"
                + "log is saved as: "
                + str(mode)
                + "_log_"
                + str(i + 1)
                + ".csv"
                + "\n"
            )
            print(
                "model weights are saved as: "
                + str(mode)
                + "_weights_"
                + str(i + 1)
                + ".h5"
                + "\n"
            )
            print(
                "model is saved as: "
                + str(mode)
                + "_model_"
                + str(i + 1)
                + ".h5"
                + "\n"
            )
            del Net
            # return Net


def perfrom_training(
    models="model_name",
    img_row=120,
    img_col=120,
    channel=3,
    dense_blocks=4,
    dense_layers=-1,
    growth_rate=12,
    bottleneck=False,
    compression=1.0,
    block_depth=40,
    final_ac_regression='sigmoid',
    batch=32,
    epoch=5,
    final_layer_no_of_nodes=3,
    regression_flag=True,
    dropout_rate_flag=True,
    batch_norm_flag=True,
    early_stopping=True,
    five_fold_flag=True,
):
    return model_training._model_training(
        models=models,
        img_row=img_row,
        img_col=img_col,
        channel=channel,
        final_ac_regression=final_ac_regression,
        dense_blocks=dense_blocks,
        dense_layers=dense_layers,
        growth_rate=growth_rate,
        bottleneck=bottleneck,
        compression=compression,
        block_depth=block_depth,
        batch=batch,
        epoch=epoch,
        final_layer_no_of_nodes=final_layer_no_of_nodes,
        regression_flag=regression_flag,
        dropout_rate_flag=dropout_rate_flag,
        batch_norm_flag=batch_norm_flag,
        early_stopping=early_stopping,
        five_fold_flag=five_fold_flag,
    )


if __name__ == "__main__":
    model_training
    perfrom_training

