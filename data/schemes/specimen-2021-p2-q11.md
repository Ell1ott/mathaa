## ### 11. (a) METHOD 1

$$ I(t)=\mathrm{e}^{\int P(t)\mathrm{d}t} $$

$$ \mathrm{e}^{\int\frac{1}{t+1}\mathrm{d}t} $$

$$ =e^{\ln(t+1)} $$

M1

## ## METHOD 2

A1 AG

attempting product rule differentiation on  $ \frac{\mathrm{d}}{\mathrm{d}t}\left(x(t+1)\right) $

$$ \frac{\mathrm{d}}{\mathrm{d}t}\big(x\big(t+1\big)\big)=\frac{\mathrm{d}x}{\mathrm{d}t}\big(t+1\big)+x $$

$$ =\left(t+1\right)\left(\frac{\mathrm{d}x}{\mathrm{d}t}+\frac{x}{t+1}\right) $$

so  $ t+1 $ is an integrating factor for this differential equation

A1

AG

[2 marks]

continued...

ST EO/OMN 100011 E/ENG 100000

Question 11 continued

(b) attempting to multiply through by  $ (t+1) $ and rearrange to give

(M1)

$$ \left(t+1\right)\frac{\mathrm{d}x}{\mathrm{d}t}+x=10\left(t+1\right)\mathrm{e}^{\frac{t}{4}} $$

A1

$$ \frac{\mathrm{d}}{\mathrm{d}t}\left(x(t+1)\right)=10(t+1)\mathrm{e}^{-\frac{t}{4}} $$

$$ x(t+1)=\int10(t+1)\mathrm{e}^{-\frac{t}{4}}\mathrm{d}t $$

A1

attempting to integrate the RHS by parts

M1

$$ =-40\left(t+1\right)\mathrm{e}^{-\frac{t}{4}}+40\int\mathrm{e}^{-\frac{t}{4}}\mathrm{d}t $$

$$ =-40(t+1)\mathrm{e}^{\frac{t}{4}}-160\mathrm{e}^{\frac{t}{4}}+C $$

A1

Note: Condone the absence of C.

## ## EITHER

substituting  $ t = 0, x = 0 \Rightarrow C = 200 $

M1

$$ x=\frac{-40\left(t+1\right)\mathrm{e}^{\frac{t}{4}}-160\mathrm{e}^{\frac{t}{4}}+200}{t+1} $$

A1

using  $ -40e^{\frac{t}{4}} $ as the highest common factor of  $ -40(t+1)e^{\frac{t}{4}} $ and  $ -160e^{\frac{t}{4}} $

OR

using $-40\mathrm{e}^{\frac{t}{4}}$ as the highest common factor of $-40(t+1)\mathrm{e}^{\frac{t}{4}}$ and $-160\mathrm{e}^{-\frac{t}{4}}$ giving $x(t+1)=-40\mathrm{e}^{-\frac{t}{4}}(t+5)+C$ (or equivalent) M1A1

substituting $t=0,x=0\Rightarrow C=200$ M1

THEN

$$ x(t)=\frac{200-40\mathrm{e}^{-\frac{t}{4}}(t+5)}{t+1} $$

AG

[8 marks]

continued...

Question 11 continued

<div style="text-align: center;">(c)</div>

<table><tr><th>t</th><th>x</th></tr><tr><td>0</td><td>0</td></tr><tr><td>4</td><td>14.6</td></tr><tr><td>60</td><td>10</td></tr></table>

$$ 0\leq t\leq60 $$

$$ 0\leq t\leq60 $$

maximum amount of salt is 14.6 (grams) at t = 6.60 (minutes)

(d) using an appropriate graph or equation (first or second derivative) amount of salt is decreasing most rapidly at $t=12.9$ (minutes)

## ## (e) EITHER

attempting to form an integral representing the amount of salt that left the tank

$$ \int\limits_{0}^{60}\frac{x(t)}{t+1}\mathrm{d}t $$

$$ \int\limits_{0}^{60}\frac{200-40\mathrm{e}^{-\frac{t}{4}}\left(t+5\right)}{\left(t+1\right)^{2}}\mathrm{d}t $$

## ## OR

attempting to form an integral representing the amount of salt that entered the tank minus the amount of salt in the tank at  $ t=60 $ (minutes)

amount of salt that left the tank is  $ \int_{0}^{60} 10 e^{\frac{t}{4}} \, \mathrm{d}t - x (60) $

THEN

=36.7(grams)

[4 marks]

Total [21 marks]
