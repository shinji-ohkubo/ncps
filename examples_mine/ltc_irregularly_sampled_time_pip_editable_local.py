#!/usr/bin/env python
# coding: utf-8

import numpy as np
import os
import ncps
from ncps import wirings
#from ncps import wirings
from ncps.tf import LTC

import matplotlib as plt
from tensorflow import keras

# ## Generating synthetic sinusoidal training data
# 
# The time dimension store the information of how much time has been elapsed **relative** since the last datapoint (i.e.,  don't confuse with the *absolute* time)


N = 48 # Length of the time-series
# Input feature is a sine and a cosine wave
data_x = np.stack(
    [np.sin(np.linspace(0, 3 * np.pi, N)), np.cos(np.linspace(0, 3 * np.pi, N))], axis=1
)
data_x = np.expand_dims(data_x, axis=0).astype(np.float32)  # Add batch dimension
data_t = np.random.default_rng().uniform(0.8,1.2, size=(1,N,1))
# Irregularly sampled time (uniform between 0.8 and 1.2 seconds)
# Target output is a sine with double the frequency of the input signal
data_y = np.sin(np.linspace(0, 6 * np.pi, N)).reshape([1, N, 1]).astype(np.float32)
print("data_x.shape: ", str(data_x.shape))
print("data_t.shape: ", str(data_t.shape))
print("data_y.shape: ", str(data_y.shape))

# Let's visualize the training data
plt.figure(figsize=(6, 4))
# To conver the relative time steps into absolute time,
# we have to do a "cumulative summation" (np.cumsum)
plt.plot(np.cumsum(data_t[0,:,0]), data_x[0, :, 0], label="Input feature 1")
plt.plot(np.cumsum(data_t[0,:,0]), data_x[0, :, 1], label="Input feature 1")
plt.plot(np.cumsum(data_t[0,:,0]), data_y[0, :, 0], label="Target output")
plt.ylim((-1, 1))
plt.title("Training data")
plt.legend(loc="upper right")
plt.show()


# ### A NCP model with irregularly sampled input


fc_wiring = wirings.AutoNCP(24, 1)  # 24 units, 1 of which is a motor neuron

input_values = keras.Input(shape=(None, 2)) # Sequence length and feature dimension
input_time = keras.Input(shape=(None,1)) # Sequence length dimension

random_dense_layer = keras.layers.Dense(32,activation="tanh") # linear layer
ltc_layer = LTC(fc_wiring, return_sequences=True)

x = random_dense_layer(input_values) # Feed values into linear layer
x = ltc_layer((x,input_time)) # feed values and time as pair into LTC RNN

model = keras.Model(inputs=(input_values,input_time),outputs=x)

model.compile(
    optimizer=keras.optimizers.Adam(0.01), loss='mean_squared_error'
)

model.summary()


# Train the model for 400 epochs (= training steps), input date is now a pair (values, elapsed time)
hist = model.fit(x=(data_x, data_t), y=data_y, batch_size=1, epochs=400,verbose=1)

