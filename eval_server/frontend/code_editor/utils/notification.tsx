import { toast } from 'react-toastify';

export const SuccessMessage = (message: string) => {
  toast.success(message, {
    position: "top-right",
    autoClose: 3000,
    hideProgressBar: false,
    closeOnClick: true,
    pauseOnHover: true,
    draggable: true,
    style: { zIndex: 10001 },
  });
};

export const ErrorMessage = (message: string) => {
  toast.error(message, {
    position: "top-right",
    autoClose: 3000,
    hideProgressBar: false,
    closeOnClick: true,
    pauseOnHover: true,
    draggable: true,
    style: { zIndex: 10001 },
  });
};

export const ErrorMessageNoAutoclose = (message: string) => {
  toast.error(message, {
    position: "top-right",
    autoClose: false,
    hideProgressBar: false,
    closeOnClick: true,
    pauseOnHover: true,
    draggable: true,
    style: { zIndex: 10001 },
  });
};

export const InfoMessage = (message: string) => {
  toast.info(message, {
    position: "top-right",
    autoClose: false,
    hideProgressBar: true,
    closeOnClick: true,
    pauseOnHover: true,
    draggable: true,
    style: { zIndex: 10001 },
  });
};

export const WarningMessage = (message: string) => {
  toast.warning(message, {
    position: "top-right",
    autoClose: 3000,
    hideProgressBar: false,
    closeOnClick: true,
    pauseOnHover: true,
    draggable: true,
    style: { zIndex: 10001 },
  });
};
