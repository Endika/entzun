/// <reference types="vite/client" />

// Para poder importar módulos CSS
declare module '*.css';
declare module '*.svg';
declare module '*.png';
declare module '*.jpg';
declare module '*.jpeg';
declare module '*.gif';
declare module '*.webp';

// Declare modules to fix TypeScript errors
declare module 'react' {
  import * as React from 'react/index';
  export = React;
  export as namespace React;
}

declare module 'react-dom' {
  export = ReactDOM;
}

declare module 'styled-components' {
  const styled: any;
  export default styled;
  export const createGlobalStyle: any;
  export const css: any;
  export const keyframes: any;
  export const ThemeProvider: any;
}

declare module 'd3' {
  export * from 'd3/index';
}

// Global namespace
declare global {
  const React: any;
  const ReactDOM: any;
  const StyledComponents: any;
  const D3: any;
  
  namespace JSX {
    interface IntrinsicElements {
      [elemName: string]: any;
    }
  }
} 