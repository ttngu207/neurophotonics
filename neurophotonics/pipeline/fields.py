import numpy as np
import datajoint as dj
from .space import Space
from matplotlib import pyplot as plt

from .. import db_prefix


schema = dj.schema(db_prefix + "photonics")


@schema
class DSim(dj.Lookup):
    definition = """
    # Detector Field Specification
    dsim : int
    ---
    dsim_description            : varchar(1024)
    detector_type = 'one-sided' : varchar(30)  # choice in simulation
    detector_width = 10.00      : decimal(5,2) # (um) along x-axis
    detector_height = 10.00     : decimal(5,2) # (um) along y-axis
    anisotropy = 0.88           : float        # factor in the Henyey-Greenstein formula
    absorption_length = 14000   : float        # (um) average travel path before an absorption event
    scatter_length = 100        : float        # (um) average travel path before a scatter event
    volume_dimx = 1000          : int unsigned # (voxels)
    volume_dimy = 1000          : int unsigned # (voxels)
    volume_dimz = 1000          : int unsigned # (voxels)
    pitch = 2.2                 : float        # (um)  spatial sampling period of the model volume
    """

    contents = []


@schema
class DField(dj.Computed):
    definition = """
    # Detector Field Reference Volume
    -> DSim
    ---
    volume        : blob@photonics # probability of a photon emitted at given point getting picked up by the given detector
    max_value     : float          # should be < 1.0
    total_photons : int unsigned
    """

    def make(self, key):
        spec = (DSim & key).fetch1()

        kwargs = {
            k: spec[k]
            for k in spec
            if k
            in {"pitch", "anisotropy", "scatter_length", "absorption_length", "detector_type"}
        }

        kwargs.update(
            dims=tuple(spec[k] for k in ("volume_dimx", "volume_dimy", "volume_dimz")),
            emitter_spread="spherical",
            emitter_size=(float(spec["detector_width"]), float(spec["detector_height"]), 0),
        )

        space = Space(**kwargs)
        space.run(hops=500_000)
        volume = space.volume * space.emitter_area
        self.insert1(
            dict(
                key,
                volume=np.float32(volume),
                max_value=volume.max(),
                total_photons=space.total_count,
            )
        )

    def plot(self, axis=None, gamma=0.7, cmap="gray_r", title=""):
        from matplotlib_scalebar.scalebar import ScaleBar

        info = (self * DSim).fetch1()
        if axis is None:
            _, axis = plt.subplots(1, 1, figsize=(8, 8))
        axis.imshow((info["volume"].sum(axis=0)) ** gamma, cmap=cmap)
        axis.axis(False)
        scale_bar = ScaleBar(info["pitch"] * 1e-6)
        axis.add_artist(scale_bar)
        title = f"{title}\n{info['total_photons'] / 1e6:0.2f} million simulated photons"
        axis.set_title(title)


@schema
class ESim(dj.Lookup):
    definition = """
    # Emission Field Specification
    esim : int
    ---
    esim_description          : varchar(1024)
    beam_compression          : float
    y_steer                   : float         # the steer angle in the plane of the shank
    emitter_width = 10.00     : decimal(5,2)  # (um) along x-axis
    emitter_height = 10.00    : decimal(5,2)  # (um) along y-axis
    anisotropy = 0.88         : float         # factor in the Henyey-Greenstein formula
    absorption_length = 14000 : float         # (um) average travel path before a absorption event
    scatter_length = 100      : float         # (um) average travel path before a scatter event
    volume_dimx = 1000        : int unsigned  # (voxels)
    volume_dimy = 1000        : int unsigned  # (voxels)
    volume_dimz = 1000        : int unsigned  # (voxels)
    beam_xy_aspect = 1.0      : float         # compression of y. E.g. 2.0 means that y is compressed by factor of 2
    pitch = 2.2               : float         # (um) spatial sampling period of the model volume
    """

    contents = []


@schema
class EField(dj.Computed):
    definition = """
    # Emitter Field Reference Volume
    -> ESim
    ---
    volume        : blob@photonics # probability of a photon emitted at given point getting picked up by the given detector
    total_photons : int unsigned
    """

    def make(self, key):
        spec = (ESim & key).fetch1()

        # pass arguments from lookup to function
        kwargs = {
            k: spec[k]
            for k in spec
            if k
            in {
                "pitch",
                "anisotropy",
                "scatter_length",
                "y_steer",
                "beam_compression",
                "beam_xy_aspect",
                "absorption_length",
            }
        }

        kwargs.update(
            dims=tuple(spec[k] for k in ("volume_dimx", "volume_dimy", "volume_dimz")),
            emitter_size=(float(spec["emitter_width"]), float(spec["emitter_height"]), 0),
        )

        space = Space(**kwargs)
        space.run(hops=500_000)
        self.insert1(dict(key, volume=np.float32(space.volume), total_photons=space.total_count))

    def plot(self, figsize=(8, 8), axis=None, gamma=0.7, cmap="magma", title=""):
        from matplotlib_scalebar.scalebar import ScaleBar

        info = (self * ESim).fetch1()
        if axis is None:
            _, axis = plt.subplots(1, 1, figsize=(8, 8))
        axis.imshow((info["volume"].sum(axis=0)) ** gamma, cmap=cmap)
        axis.axis(False)
        scale_bar = ScaleBar(info["pitch"] * 1e-6)
        axis.add_artist(scale_bar)
        title = f"{title}\n{info['total_photons'] / 1e6:0.2f} million simulated photons"
        axis.set_title(title)


# @schema
# class Efield2dimage(dj.Computed):
#     definition = """
#     # Emission field images in 2D.
#     -> Esim
#     pov: smallint  # point of view direction (compression direction)
#     ---
#     projected_image: blob@photonics
#     """

#     def make(self, key):
#         volume = (EField & key).fetch1("volume")  # There will be only 1 volume per key.

#         for pov in [0, 1, 2]:
#             self.insert1(dict(key, pov=pov, projected_image=volume.sum(axis=pov)))
