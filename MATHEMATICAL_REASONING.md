# Mathematical Justification

This document formally justifies the mathematical frameworks selected for modeling the Stockholm Metro transit delays. Because public transit delays are highly non-normal, spatially correlated, and subject to right-censoring, standard independent and identically distributed (i.i.d.) regression algorithms (e.g., OLS, Random Forests) are insufficient. 

The following models were developed to address these constraints rigorously.

---

## 1. Spatio-Temporal Graph Convolutional Networks (STGCN)

Standard multivariate time-series models like Vector Autoregression (VAR) fail to scale due to $O(N^2)$ parameter growth and ignore the physical constraints of the transit network. 

**Mathematical Formulation:**
We model the Stockholm Metro as a directed, weighted graph $\mathcal{G} = (\mathcal{V}, \mathcal{E}, A)$, where $\mathcal{V}$ represents stations, $\mathcal{E}$ the tracks, and $A \in \mathbb{R}^{N \times N}$ is the adjacency matrix weighted by track distance.

To capture the topological propagation of delays, we apply spectral graph convolutions. Using the first-order approximation of Chebyshev polynomials, the spatial convolution at layer $l$ is defined as:
$$H^{(l+1)} = \sigma\left(\tilde{D}^{-\frac{1}{2}} \tilde{A} \tilde{D}^{-\frac{1}{2}} H^{(l)} \Theta\right)$$
Where:
*   $\tilde{A} = A + I_N$ is the adjacency matrix with added self-loops.
*   $\tilde{D}_{ii} = \sum_j \tilde{A}_{ij}$ is the diagonal degree matrix.
*   $H^{(l)}$ are the hidden node embeddings, and $\Theta$ is the learnable weight matrix.

**Justification:**
This formulation acts as a localized low-pass filter on the graph signal. It mathematically restricts the receptive field so that the predicted delay at station $v_i$ is only a function of its physical neighbors, avoiding the calculation of spurious correlations between entirely disconnected train lines. The temporal evolution is subsequently captured by passing the spatial embeddings $H$ through a Gated Recurrent Unit (GRU), effectively modeling $P(X_{t+1} | \mathcal{G}, X_{t}, ..., X_{t-k})$.

---

## 2. Bayesian Structural Time Series (State Space Models)

A major challenge in transit modeling is distinguishing between transient delays (aleatoric noise) and systemic network failures (structural breaks). 

**Mathematical Formulation:**
We define a linear Gaussian state space model consisting of an observation equation and a state transition equation:
$$y_t = Z_t \alpha_t + \varepsilon_t, \quad \varepsilon_t \sim \mathcal{N}(0, H_t)$$
$$\alpha_{t+1} = T_t \alpha_t + R_t \eta_t, \quad \eta_t \sim \mathcal{N}(0, Q_t)$$

We structure the latent state $\alpha_t$ as an Unobserved Components model containing a local level $\mu_t$ (representing baseline network congestion) and a seasonal component $\gamma_t$ (representing daily rush-hour harmonics):
$$\mu_{t+1} = \mu_t + \xi_t$$
$$\gamma_t = \sum_{j=1}^{S/2} \left[ a_j \cos(\lambda_j t) + b_j \sin(\lambda_j t) \right]$$

**Justification:**
By utilizing the Kalman Filter, we can perform exact Bayesian inference to estimate the posterior distribution of the hidden states $P(\alpha_t | y_{1:t})$. Unlike black-box neural networks, this provides mathematically rigorous credible intervals for our predictions. It explicitly models a major track failure as a sudden shock to the random walk $\mu_t$ rather than treating it as an outlier to be smoothed over.

---

## 3. Survival Analysis (Cox Proportional Hazards)

Predicting the absolute severity of a delay in seconds using standard regression fundamentally violates the OLS assumption of normally distributed residuals, as delay times are strictly positive $\mathbb{R}^+$ and heavily right-skewed.

**Mathematical Formulation:**
Instead of regression, we reframe the problem using Survival Analysis. Let $T$ be the continuous random variable representing the time until a train arrives at a station. We model the hazard function $h(t|x)$, which represents the instantaneous rate of arrival given that it has not yet arrived, conditioned on covariates $x$ (e.g., weather, time of day):
$$h(t|x) = h_0(t) \exp(\beta^T x)$$
Where:
*   $h_0(t)$ is the non-parametric baseline hazard function.
*   $\exp(\beta^T x)$ is the partial hazard, representing the multiplicative effect of the covariates.

**Justification:**
This approach provides two critical mathematical advantages:
1.  **Non-Normality**: It makes no assumptions about the underlying distribution of the delay times, effortlessly handling the heavy tails of extreme transit delays.
2.  **Right-Censoring**: In real-time predictive systems, we observe trains that are currently delayed but *have not arrived yet*. Standard regression must drop these observations or wait until completion. The Cox model natively incorporates this right-censored data via the partial likelihood function, ensuring unbiased parameter estimation $\hat{\beta}$ even during live incidents.
