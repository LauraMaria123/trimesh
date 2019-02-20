import numpy as np

try:
    from scipy.sparse import coo_matrix
except ImportError:
    pass


def filter_laplacian(mesh,
                     lamb=0.5,
                     iterations=10,
                     laplacian_operator=None):
    """

    Smooth a mesh in-place using laplacian smoothing.

    Articles
    "Improved Laplacian Smoothing of Noisy Surface Meshes"
    J. Vollmer, R. Mencl, and H. Muller

    Parameters
    ------------
    mesh : trimesh.Trimesh
      Mesh to be smoothed in place
    lamb : float
      Diffusion speed constant
      If 0.0, no diffusion
      If 1.0, full diffusion
    iterations : int
      Number of passes to run filter
    laplacian_operator : None or scipy.sparse.coo.coo_matrix
      Sparse matrix laplacian operator
      Will be autogenerated if None
    """
    # if the laplacian operator was not passed create it here
    if laplacian_operator is None:
        laplacian_operator = laplacian_calculation(mesh)

    # get mesh vertices as vanilla numpy array
    vertices = mesh.vertices.copy().view(np.ndarray)

    # Number of passes
    for _index in range(iterations):
        dot = coo_matrix.dot(laplacian_operator, vertices) - vertices
        vertices += lamb * dot

    # assign modified vertices back to mesh
    mesh.vertices = vertices
    return mesh


def filter_humphrey(mesh,
                    alpha=0.1,
                    beta=0.5,
                    iterations=10,
                    laplacian_operator=None):
    """
    Smooth a mesh in-place using laplacian smoothing
    and Humphrey filtering.

    Articles
    "Improved Laplacian Smoothing of Noisy Surface Meshes"
    J. Vollmer, R. Mencl, and H. Muller

    Parameters
    ------------
    mesh : trimesh.Trimesh
      Mesh to be smoothed in place
    alpha : float
      Controls shrinkage, range is 0.0 - 1.0
      If 0.0, not considered
      If 1.0, no smoothing
    beta : float
      Controls how aggressive smoothing is
      If 0.0, no smoothing
      If 1.0, full aggressiveness
    iterations : int
      Number of passes to run filter
    laplacian_operator : None or scipy.sparse.coo.coo_matrix
      Sparse matrix laplacian operator
      Will be autogenerated if None
    """
    # if the laplacian operator was not passed create it here
    if laplacian_operator is None:
        laplacian_operator = laplacian_calculation(mesh)

    # get mesh vertices as vanilla numpy array
    vertices = mesh.vertices.copy().view(np.ndarray)
    # save original unmodified vertices
    original = vertices.copy()

    # run through iterations of filter
    for _index in range(iterations):
        vert_q = vertices.copy()
        vertices = laplacian_operator.dot(vertices)
        vert_b = vertices - (alpha * original + (1.0 - alpha) * vert_q)
        vertices -= (beta * vert_b + (1.0 - beta) *
                     laplacian_operator.dot(vert_b))

    # assign modified vertices back to mesh
    mesh.vertices = vertices
    return mesh


def filter_taubin(mesh,
                  lamb=0.5,
                  nu=0.5,
                  iterations=10,
                  laplacian_operator=None):
    """
    Smooth a mesh in-place using laplacian smoothing
    and taubin filtering.

    Articles
    "Improved Laplacian Smoothing of Noisy Surface Meshes"
    J. Vollmer, R. Mencl, and H. Muller

    Parameters
    ------------
    mesh : trimesh.Trimesh
      Mesh to be smoothed in place.
    lamb : float
      Controls shrinkage, range is 0.0 - 1.0
    nu : float
      Controls dilation, range is 0.0 - 1.0
      Nu shall be between 0.0 < 1.0/lambda - 1.0/nu < 0.1
    iterations : int
      Number of passes to run the filter
    laplacian_operator : None or scipy.sparse.coo.coo_matrix
      Sparse matrix laplacian operator
      Will be autogenerated if None
    """
    # if the laplacian operator was not passed create it here
    if laplacian_operator is None:
        laplacian_operator = laplacian_calculation(mesh)

    # get mesh vertices as vanilla numpy array
    vertices = mesh.vertices.copy().view(np.ndarray)

    # run through multiple passes of the filter
    for index in range(iterations):
        # do a sparse dot product on the vertices
        dot = laplacian_operator.dot(vertices) - vertices
        # alternate shrinkage and dilation
        if index % 2 == 0:
            vertices += lamb * dot
        else:
            vertices -= nu * dot

    # assign updated vertices back to mesh
    mesh.vertices = vertices
    return mesh


def laplacian_calculation(mesh, equal_weight=True):
    """
    Calculate a sparse matrix for laplacian operations.

    Parameters
    -------------
    mesh : trimesh.Trimesh
      Input geometry
    equal_weight : bool
      If True, all neighbors will be considered equally
      If False, all neightbors will be weighted by inverse distance

    Returns
    ----------
    laplacian : scipy.sparse.coo.coo_matrix
      Laplacian operator
    """
    # get the vertex neighbors from the cache
    neighbors = mesh.vertex_neighbors
    # avoid hitting crc checks in loops
    vertices = mesh.vertices.view(np.ndarray)

    # stack neighbors to 1D arrays
    col = np.concatenate(neighbors)
    row = np.concatenate([[i] * len(n)
                          for i, n in enumerate(neighbors)])

    if equal_weight:
        # equal weights for each neighbor
        data = np.concatenate([[1.0 / len(n)] * len(n)
                               for n in neighbors])
    else:
        # umbrella weights, distance-weighted
        # use dot product of ones to replace array.sum(axis=1)
        ones = np.ones(3)
        # the distance from verticesex to neighbors
        norms = [1.0 / np.sqrt(np.dot((vertices[i] - vertices[n]) ** 2, ones))
                 for i, n in enumerate(neighbors)]
        # normalize group and stack into single array
        data = np.concatenate([i / i.sum() for i in norms])

    # create the sparse matrix
    matrix = coo_matrix((data, (row, col)),
                        shape=[len(vertices)] * 2)

    return matrix
