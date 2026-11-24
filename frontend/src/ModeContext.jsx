import { createContext, useContext } from "react";

export const ModeCtx = createContext({ mode: "light", toggle: () => {} });
export const useMode = () => useContext(ModeCtx);
