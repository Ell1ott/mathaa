12. (a) attempting to use the chain rule to find the first derivative  $ f'(x) = (\cos x) e^{\sin x} $ M1 A1

$$ f^{\prime \prime}\left(x\right)=\mathrm{e}^{\sin x}\left(\cos^{2}x-\sin x\right) $$

attempting to find $f(0)$, $f^{\prime}(0)$ and $f^{\prime \prime}(0)$

$$ f(0)=1;\;f^{\prime}(0)=\left(\cos0\right)\mathrm{e}^{\sin0}=1;\;f^{\prime \prime}(0)=\mathrm{e}^{\sin0}\left(\cos^{2}0-\sin0\right)=1 $$

A1

substitution into the Maclaurin formula  $ f(x) = f(0) + x f'(0) + \frac{x^2}{2!} f''(0) + \ldots $

M1

so the Maclaurin series for  $ f(x) $ up to and including the  $ x^{2} $ term is  $ 1 + x + \frac{x^{2}}{2} $ A1

## ## (b) METHOD 1

[8 marks]

attempting to differentiate  $ f''(x) $

$$ f^{m}(x)=(\cos x)\mathrm{e}^{\sin x}\left(\cos^{2}x-\sin x\right)-(\cos x)\mathrm{e}^{\sin x}\left(2\sin x+1\right)\mathrm{\ (o r~e q u i v a l e n t)\ }\quad A2 $$

substituting $x=0$ into their $f'''(x)$

M1

$$ f^{m}(0)=1(1-0)-1(0+1)=0 $$

so the coefficient of  $ x^{3} $ in the Maclaurin series for  $ f(x) $ is zero

AG

## ## METHOD 2

substituting  $ \sin x $ into the Maclaurin series for  $ e^{x} $

(M1)

$$ \mathbf{e}^{\sin x}=1+\sin x+\frac{\sin^{2}x}{2!}+\frac{\sin^{3}x}{3!}+\ldots $$

substituting Maclaurin series for  $ \sin x $

M1

$$ \mathrm{e}^{\sin x}=1+\left(x-\frac{x^{3}}{3!}+\ldots\right)+\frac{\left(x-\frac{x^{3}}{3!}+\ldots\right)^{2}}{2!}+\frac{\left(x-\frac{x^{3}}{3!}+\ldots\right)^{3}}{3!}+\ldots $$

A1

coefficient of  $ x^3 $ is  $ -\frac{1}{3!} + \frac{1}{3!} = 0 $

so the coefficient of  $ x^{3} $ in the Maclaurin series for  $ f(x) $ is zero

[4 marks]

continued...

Question 12 continued

(c) substituting 3x into the Maclaurin series for  $ e^{x} $

M1

$$ \mathbf{e}^{3x}=1+3x+\frac{\left(3x\right)^{2}}{2!}+\frac{\left(3x\right)^{3}}{3!}+\ldots $$

A1

substituting  $ (\mathrm{e}^{3x}-1) $ into the Maclaurin series for  $ \arctan x $

M1

$$ \begin{aligned}&\arctan\left(\mathrm{e}^{3x}-1\right)=\left(\mathrm{e}^{3x}-1\right)-\frac{\left(\mathrm{e}^{3x}-1\right)^{3}}{3}+\frac{\left(\mathrm{e}^{3x}-1\right)^{5}}{5}-\ldots\\ &=\left(3x+\frac{\left(3x\right)^{2}}{2!}+\frac{\left(3x\right)^{3}}{3!}+\cdots\right)-\frac{\left(3x+\frac{\left(3x\right)^{2}}{2!}+\frac{\left(3x\right)^{3}}{3!}+\cdots\right)^{3}}{3}+\ldots\\ &selecting~correct~terms~from~above\\ &=\left(3x+\frac{\left(3x\right)^{2}}{2!}+\frac{\left(3x\right)^{3}}{3!}\right)-\frac{\left(3x\right)^{3}}{3}\\ &=3x+\frac{9x^{2}}{2}-\frac{9x^{3}}{2}\\ \end{aligned} $$

A1

M1

## ## (d) METHOD 1

A1

substitution of their series

$$ \begin{aligned}&\lim_{x\rightarrow0}\frac{x+\frac{x^{2}}{2}+\ldots}{3x+\frac{9x^{2}}{2}+\ldots}\\&=\lim_{x\rightarrow0}\frac{1+\frac{x}{2}+\ldots}{3+\frac{9x}{2}+\ldots}\\&=\frac{1}{3}\end{aligned} $$

## ## METHOD 2

[6 marks]

use of l'Hôpital's rule

$$ \begin{aligned}&\lim_{x\to0}\frac{\left(\cos x\right)\mathrm{e}^{\sin x}}{3\mathrm{e}^{3x}}\quad(or~equivalent)\\&=\frac{1}{3}\end{aligned} $$

M1

A1

[3 marks]

Total [21 marks]
