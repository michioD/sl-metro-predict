import torch
import torch.nn as nn
import torch.nn.functional as F

class GraphConvolution(nn.Module):
    """
    Simple Spatial Graph Convolution layer.
    Computes H^(l+1) = sigma(D^(-1/2) A D^(-1/2) H^(l) W)
    """
    def __init__(self, in_features, out_features):
        super(GraphConvolution, self).__init__()
        self.weight = nn.Parameter(torch.FloatTensor(in_features, out_features))
        self.bias = nn.Parameter(torch.FloatTensor(out_features))
        self.reset_parameters()

    def reset_parameters(self):
        nn.init.xavier_uniform_(self.weight)
        nn.init.zeros_(self.bias)

    def forward(self, text_features, adj_matrix):
        # text_features: (Batch, Nodes, Features)
        # adj_matrix: (Nodes, Nodes) normalized Laplacian
        support = torch.matmul(text_features, self.weight)
        output = torch.matmul(adj_matrix, support)
        return output + self.bias

class STGCN(nn.Module):
    """
    Spatio-Temporal Graph Convolutional Network for Metro Delay Prediction.
    Models the topological propagation of delays across stations (Spatial via GCN)
    and the chronological evolution of those delays (Temporal via GRU).
    """
    def __init__(self, num_nodes, in_features, hidden_features, seq_len):
        super(STGCN, self).__init__()
        self.num_nodes = num_nodes
        self.seq_len = seq_len
        
        # Spatial Graph Convolution
        self.gcn1 = GraphConvolution(in_features, hidden_features)
        self.gcn2 = GraphConvolution(hidden_features, hidden_features)
        
        # Temporal Gated Recurrent Unit
        self.gru = nn.GRU(hidden_features * num_nodes, hidden_features, batch_first=True)
        
        # Output fully connected layer to predict delay at all nodes
        self.fc = nn.Linear(hidden_features, num_nodes)

    def forward(self, x, adj):
        # x shape: (Batch, Seq_Len, Nodes, Features)
        batch_size = x.size(0)
        
        # Apply GCN to each time step independently
        gcn_outputs = []
        for t in range(self.seq_len):
            x_t = x[:, t, :, :]
            h_t = F.relu(self.gcn1(x_t, adj))
            h_t = F.relu(self.gcn2(h_t, adj))
            # Flatten nodes and features for the temporal sequence
            gcn_outputs.append(h_t.view(batch_size, -1))
            
        # Shape: (Batch, Seq_Len, Nodes * hidden_features)
        temporal_seq = torch.stack(gcn_outputs, dim=1)
        
        # Pass through GRU to model temporal dependencies
        out, hidden = self.gru(temporal_seq)
        
        # Decode the final hidden state to predict delays at all stations
        # hidden shape: (1, Batch, hidden_features)
        predictions = self.fc(hidden.squeeze(0))
        return predictions

def train_stgcn_epoch(model, dataloader, optimizer, adj_matrix):
    """Training loop for one epoch of STGCN."""
    model.train()
    total_loss = 0
    criterion = nn.MSELoss()
    
    for x_batch, y_batch in dataloader:
        optimizer.zero_grad()
        # Predict delays for the next time step
        preds = model(x_batch, adj_matrix)
        loss = criterion(preds, y_batch)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
        
    return total_loss / len(dataloader)
