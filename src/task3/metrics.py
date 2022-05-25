"""
Metrics for IAM
"""

import tensorflow as tf
from jiwer import wer, cer

from preprocessing import LabelEncoder, LabelPadding


class ErrorRateCallback(tf.keras.callbacks.Callback):
    """
    Calculates and prints WER & CER for validation dataset each epoch.
    Also saves WER & CER to log_dir if provided.
    Implemented as callback instead of metric for simplicity.
    """

    def __init__(self,
                 val_ds: tf.data.Dataset,
                 label_encoder: LabelEncoder,
                 label_padding: LabelPadding,
                 log_dir: str = None,
                 ctc_blank: int = -1) -> None:
        """
        Needs extra utilities to remove padding and decode labels.

        :param val_ds: validation data
        :param label_encoder: to decode labels
        :param label_padding: to remove padding from labels
        :param log_dir: path to logs folder
        :param ctc_blank: padding character to remove
        """

        super(ErrorRateCallback, self).__init__()
        self.val_ds = val_ds
        self.label_encoder = label_encoder
        self.label_padding = label_padding
        self.ctc_blank = ctc_blank
        self.writer = None
        if log_dir is not None:
            self.writer = tf.summary.create_file_writer(logdir=str(log_dir))

    def on_epoch_end(self, epoch, logs=None) -> None:
        wer_epoch = []
        cer_epoch = []

        # get prediction for each batch in validation set
        for batch in iter(self.val_ds):
            y_pred = self.model.predict(batch)
            y_pred = tf.convert_to_tensor(y_pred, dtype=tf.int64)

            # get wer & cer for each sample in the batch
            for i, (img, y_true) in enumerate(zip(batch["Image"], batch["Label"])):
                y_true = self.label_padding.remove(y_true)
                y_true = self.label_encoder.decode(y_true)
                output = y_pred[i]
                output = self.label_padding.remove(output, pad_value=self.ctc_blank)
                output = self.label_encoder.decode(output)
                wer_epoch.append(wer(y_true, output))
                cer_epoch.append(cer(y_true, output))

        # get mean wer & cer
        mean_wer = tf.reduce_mean(wer_epoch)
        mean_cer = tf.reduce_mean(cer_epoch)

        # write wer & cer to logdir
        if self.writer is not None:
            print("write error rate to file...")
            with self.writer.as_default(step=epoch):
                tf.summary.histogram('wer', tf.convert_to_tensor(wer_epoch), step=epoch)
                tf.summary.histogram('cer', tf.convert_to_tensor(cer_epoch), step=epoch)

        print(
            f"WER for epoch {epoch + 1}: {mean_wer:.4f}\n"
            f"CER for epoch {epoch + 1}: {mean_cer:.4f}"
        )
